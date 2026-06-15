from gsi_ebd.models.user import User, Role
from gsi_ebd.models.study import Study, StudyVersion, StudyAssignment
from gsi_ebd.models.progress import UserResponse, Progress


def test_user_role_enum():
    assert Role.ADMIN == 1
    assert Role.SUPERVISOR == 2
    assert Role.GESTOR == 3
    assert Role.ALUNO == 4


def test_user_model_fields():
    user = User(email="test@test.com", password_hash="hash", nome="Teste", role=Role.ALUNO)
    assert user.email == "test@test.com"
    assert user.nome == "Teste"
    assert user.role == Role.ALUNO
    assert user.is_active is True


def test_study_model_fields():
    study = Study(title="Teste", description="Desc", category="geral")
    assert study.title == "Teste"
    assert study.is_active is True


def test_study_version_fields():
    version = StudyVersion(study_id=1, version=1, content_md="content", questions_json="[]")
    assert version.version == 1
    assert version.content_md == "content"


def test_progress_fields():
    progress = Progress(user_id=1, study_id=1, score=85.0, total_questions=10, correct_answers=8)
    assert progress.score == 85.0
    assert progress.correct_answers == 8
