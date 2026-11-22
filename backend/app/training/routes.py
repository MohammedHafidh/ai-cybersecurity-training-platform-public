from datetime import datetime, timezone
import os
import secrets
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.training.content import SCENARIOS, lesson
from app.training.contracts import ScenarioKey, StartExercise, QuizSubmission
from app.training.storage import Exercise, QuizAttempt
from app.training import lab, worker
from app.persistence.runtime import request_engine

TOKEN = secrets.token_urlsafe(32)

router = APIRouter(prefix="/training", tags=["training"])

@router.get("/scenarios")
def scenarios():
    return [lesson(key) for key in SCENARIOS]

@router.get("/scenarios/{scenario}")
def guide(scenario: ScenarioKey):
    return lesson(scenario)


def local_request(request):
    host = request.url.hostname
    if host not in ("localhost", "127.0.0.1", "::1", "testserver"):
        raise HTTPException(403, "Platform controls are local only")
    if request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
        raise HTTPException(403, "Platform controls are local only")
    origin = request.headers.get("origin")
    expected = os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")
    if origin and origin != expected: raise HTTPException(403, "Unapproved browser origin")


def control(request: Request):
    local_request(request)
    if request.headers.get("origin") != os.getenv("FRONTEND_ORIGIN", "http://localhost:8000"):
        raise HTTPException(403, "A same-origin browser request is required")
    if not secrets.compare_digest(request.headers.get("x-capstone-token", ""), TOKEN):
        raise HTTPException(403, "Refresh the platform to restore the local control session")
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise HTTPException(415, "JSON is required")
    if os.getenv("CAPSTONE_TRAINING_ENABLED") != "1": raise HTTPException(503, "Training controls are disabled")


@router.get("/session")
def local_session(request: Request):
    local_request(request)
    return {"token":TOKEN}


@router.get("/readiness")
def readiness(request: Request):
    local_request(request)
    if os.getenv("CAPSTONE_TRAINING_ENABLED") != "1":return {"ready":False,"message":"The operator has not enabled training controls."}
    with request_engine(request) as engine:
        if engine.dialect.name != "postgresql":return {"ready":False,"message":"Training exercises require the configured PostgreSQL service."}
        with Session(engine) as session:
            if session.scalar(select(Exercise.id).where(Exercise.active_slot==1)):
                return {"ready":False,"message":"Another exercise is in progress. Wait for it to finish."}
    return lab.readiness()


def view(row):
    return {"id":row.id,"scenario":row.scenario,"mode":row.mode,"status":row.status,"stage":row.stage,"history":row.history,"error":row.error,"result":row.result,"completed":row.completed_at is not None}


@router.post("/exercises",status_code=202,dependencies=[Depends(control)])
def start(body: StartExercise, request: Request):
    if body.mode=="live" and not lab.readiness()["ready"]:raise HTTPException(503,lab.readiness()["message"])
    with request_engine(request) as engine:
        if engine.dialect.name != "postgresql":raise HTTPException(503,"Training exercises require PostgreSQL")
        with Session(engine) as session:
            row=Exercise(id=uuid4().hex,scenario=body.scenario,mode=body.mode,active_slot=1,status="running",stage="preparing",history=[{"stage":"preparing","at":lab.utc().isoformat()}],result={},error="")
            session.add(row)
            try:session.commit()
            except IntegrityError:raise HTTPException(409,"Another exercise is already in progress") from None
            output=view(row)
            worker.launch(engine,row)
    return output


@router.get("/exercises/{exercise}")
def exercise(exercise: str, request: Request):
    local_request(request)
    with request_engine(request) as engine,Session(engine) as session:
        row=session.get(Exercise,exercise)
        if row is None:raise HTTPException(404,"Exercise not found")
        output=view(row)
        output["quiz_attempts"]=[{"id":a.id,"answers":a.answers,"score":a.score,"passed":bool(a.passed),"at":a.created_at.isoformat()} for a in session.scalars(select(QuizAttempt).where(QuizAttempt.exercise_id==exercise).order_by(QuizAttempt.created_at))]
        return output


@router.post("/exercises/{exercise}/cancel",dependencies=[Depends(control)])
def cancel(exercise: str):
    with worker.LOCK:event=worker.CANCELS.get(exercise)
    if event is None:raise HTTPException(409,"Exercise is not active")
    event.set()
    return {"status":"cancellation_requested"}


@router.post("/exercises/{exercise}/quiz-attempts",dependencies=[Depends(control)])
def grade(exercise: str,body: QuizSubmission,request: Request):
    with request_engine(request) as engine,Session(engine) as session,session.begin():
        row=session.get(Exercise,exercise)
        if row is None:raise HTTPException(404,"Exercise not found")
        if row.status!="ready":raise HTTPException(409,"Review the completed exercise evidence first")
        content=lesson(row.scenario,answers=True); questions=content["questions"]
        if any(type(a) is not int or not 0<=a<4 for a in body.answers):raise HTTPException(422,"Choose one option for each question")
        score=sum(a==q["correct"] for a,q in zip(body.answers,questions,strict=True))
        attempt=QuizAttempt(id=uuid4().hex,exercise_id=exercise,version=content["version"],answers=body.answers,score=score,passed=int(score>=3))
        session.add(attempt)
        return {"score":score,"total":4,"passed":score>=3,"feedback":[{"correct":a==q["correct"],"answer":q["correct"],"explanation":q["explanation"]} for a,q in zip(body.answers,questions,strict=True)]}


@router.post("/exercises/{exercise}/complete",dependencies=[Depends(control)])
def complete(exercise: str,request: Request):
    with request_engine(request) as engine,Session(engine) as session,session.begin():
        row=session.get(Exercise,exercise)
        if row is None:raise HTTPException(404,"Exercise not found")
        passed=session.scalar(select(QuizAttempt.id).where(QuizAttempt.exercise_id==exercise,QuizAttempt.passed==1))
        if row.status!="ready" or not passed:raise HTTPException(409,"Complete the evidence review and pass the quiz first")
        row.completed_at=datetime.now(timezone.utc)
        return {"completed":True}
