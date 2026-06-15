from typing import Optional

try:
    from langchain_community.llms import Ollama
    from langchain_core.prompts import ChatPromptTemplate
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


EXPLAINER_SYSTEM = """Voce e um explicador de contexto biblico.
Sua funcao e fornecer contexto historico, cultural e teologico para passagens biblicas.
Sempre mantenha fidelidade a Escritura. Responda em portugues brasileiro."""

TUTOR_SYSTEM = """Voce e um tutor virtual de estudos biblicos.
Ajude o aluno a compreender melhor a licao, faca perguntas reflexivas
e oriente sem dar respostas diretas. Responda em portugues brasileiro."""

EVALUATOR_SYSTEM = """Voce e um avaliador de respostas biblicas.
Analise a resposta do aluno considerando fidelidade biblica,
clareza e profundidade. Dê feedback construtivo. Responda em portugues."""


class ExplainerAgent:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        if _AVAILABLE:
            self._llm = Ollama(base_url=base_url, model=model)
        else:
            self._llm = None

    async def explain(self, passage: str, question: str = "") -> str:
        if not self._llm:
            return "Agente nao disponivel. Configure Ollama."
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", EXPLAINER_SYSTEM),
                ("human", "Passagem: {passage}\nPergunta: {question}\nExplique o contexto:"),
            ])
            chain = prompt | self._llm
            result = await chain.ainvoke({"passage": passage, "question": question})
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Erro: {e}"


class TutorAgent:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        if _AVAILABLE:
            self._llm = Ollama(base_url=base_url, model=model)
        else:
            self._llm = None

    async def guide(self, lesson_content: str, student_question: str) -> str:
        if not self._llm:
            return "Tutor nao disponivel. Configure Ollama."
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", TUTOR_SYSTEM),
                ("human", "Licao: {lesson}\nPergunta do aluno: {question}\nOriente o aluno:"),
            ])
            chain = prompt | self._llm
            result = await chain.ainvoke({"lesson": lesson_content, "question": student_question})
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Erro: {e}"


class EvaluatorAgent:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        if _AVAILABLE:
            self._llm = Ollama(base_url=base_url, model=model)
        else:
            self._llm = None

    async def evaluate(self, question: str, answer: str, context: str) -> str:
        if not self._llm:
            return "Avaliador nao disponivel. Configure Ollama."
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", EVALUATOR_SYSTEM),
                ("human", "Questao: {question}\nResposta: {answer}\nContexto: {context}\nAvalie:"),
            ])
            chain = prompt | self._llm
            result = await chain.ainvoke({"question": question, "answer": answer, "context": context})
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Erro: {e}"
