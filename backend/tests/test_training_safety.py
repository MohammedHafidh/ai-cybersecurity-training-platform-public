from copy import deepcopy
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.training import lab
from app.training.contracts import QuizSubmission
from pydantic import ValidationError
from test_ingestion_api import database


def test_no_execution_without_valid_local_browser_control(database, monkeypatch):
    monkeypatch.setenv("CAPSTONE_TRAINING_ENABLED", "1")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:8000")
    def forbidden(): raise AssertionError("Lab must not be reached")
    monkeypatch.setattr(lab, "readiness", forbidden)
    with TestClient(app) as client:
        token=client.get('/training/session').json()['token']
        body={'scenario':'brute-force','mode':'live'}
        assert client.post('/training/exercises',json=body).status_code==403
        assert client.post('/training/exercises',json=body,headers={'Origin':'https://untrusted.invalid','X-Capstone-Token':token}).status_code==403
        headers={'Origin':'http://localhost:8000','X-Capstone-Token':token}
        assert client.post('/training/exercises',json=dict(body,target='external.invalid'),headers=headers).status_code==422
        assert client.post('/training/exercises',json=body,headers={**headers,'Host':'external.invalid'}).status_code==403


@pytest.mark.parametrize('change', ['external','ports','privileged','bind','owner','attachment'])
def test_unsafe_runtime_topology_is_rejected(change):
    id=uuid4().hex;network={'Name':'owned_lab','Internal':True,'Containers':{'a':{},'b':{}}}
    c={'HostConfig':{},'Config':{'Labels':{'capstone.exercise':id,'com.docker.compose.project':lab.project_name(id)}},'NetworkSettings':{'Networks':{'owned_lab':{}}}}
    containers=[deepcopy(c),deepcopy(c)]
    lab.validate_isolation(containers,network,id)
    if change=='external':network['Internal']=False
    elif change=='ports':containers[0]['HostConfig']['PortBindings']={'22/tcp':[{'HostPort':'2222'}]}
    elif change=='privileged':containers[0]['HostConfig']['Privileged']=True
    elif change=='bind':containers[0]['HostConfig']['Binds']=['/:/host']
    elif change=='owner':containers[0]['Config']['Labels']['capstone.exercise']='other'
    else:containers[0]['NetworkSettings']['Networks']['bridge']={}
    with pytest.raises(ValueError):lab.validate_isolation(containers,network,id)


def test_server_project_names_and_quiz_answers_are_strict():
    with pytest.raises(ValueError):lab.project_name('external; command')
    with pytest.raises(ValidationError):QuizSubmission(answers=[True,0,0,0])
    with pytest.raises(ValidationError):QuizSubmission(answers=[4,0,0,0])
