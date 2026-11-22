from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.main import app
from app.training.storage import Exercise, QuizAttempt
from test_ingestion_api import database


def test_quiz_grading_persistence_and_completion_are_independent_of_detectors(database,monkeypatch):
    monkeypatch.setenv('CAPSTONE_TRAINING_ENABLED','1');monkeypatch.setenv('FRONTEND_ORIGIN','http://localhost:8000')
    with TestClient(app) as client:
        key=uuid4().hex
        with Session(app.state.database_engine) as s,s.begin():s.add(Exercise(id=key,scenario='brute-force',mode='sample',status='ready',stage='ready',history=[],result={},error=''))
        headers={'Origin':'http://localhost:8000','X-Capstone-Token':client.get('/training/session').json()['token']}
        path='/training/exercises/'+key
        assert client.post(path+'/complete',json={},headers=headers).status_code==409
        failed=client.post(path+'/quiz-attempts',json={'answers':[3,3,3,0]},headers=headers).json()
        assert failed['score']==0 and not failed['passed']
        assert all(row['explanation'] for row in failed['feedback'])
        assert client.post(path+'/complete',json={},headers=headers).status_code==409
        passed=client.post(path+'/quiz-attempts',json={'answers':[0,2,1,0]},headers=headers).json()
        assert passed['score']==3 and passed['passed']
        assert client.post(path+'/complete',json={},headers=headers).json()['completed']
        with Session(app.state.database_engine) as s:
            attempts=list(s.scalars(select(QuizAttempt).where(QuizAttempt.exercise_id==key)))
            assert len(attempts)==2 and all(a.created_at and len(a.answers)==4 for a in attempts)
        state=client.get(path).json();assert state['completed'] and len(state['quiz_attempts'])==2
        assert client.post(path+'/quiz-attempts',json={'answers':[True,2,1,3]},headers=headers).status_code==422
