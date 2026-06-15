from typing import Optional

import reflex as rx

try:
    from langchain_community.llms import Ollama
    from langchain_core.prompts import ChatPromptTemplate

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False


EXPLAIN_PROMPT = """Voce é um assistente de estudos biblicos fiel a Escritura.
Com base no texto biblico e na licao abaixo, explique o contexto de forma clara
para um estudante iniciante. Use linguagem acessivel e mantenha fidelidade a Biblia.

Texto biblico: {verse}
Licao: {lesson_content}

Explicacao:"""

QUIZ_PROMPT = """Voce é um gerador de questoes biblicas.
Com base na licao abaixo, gere {count} questoes do tipo {question_type}.
Cada questao deve ter: key, type, question, options (se multiplo), answer.

Licao: {lesson_content}

Responda apenas com JSON valido (lista de objetos)."""


class AIService:
    _llm: Optional[object] = None
    _base_url: str = "http://localhost:11434"
    _model: str = "llama3"

    @classmethod
    def configure(cls, base_url: str = "http://localhost:11434", model: str = "llama3"):
        cls._base_url = base_url
        cls._model = model
        if _LANGCHAIN_AVAILABLE:
            cls._llm = Ollama(base_url=base_url, model=model)

    @classmethod
    async def explain_context(cls, verse: str, lesson_content: str) -> str:
        if not _LANGCHAIN_AVAILABLE or cls._llm is None:
            return "IA nao disponivel. Configure Ollama e LangChain."
        try:
            prompt = ChatPromptTemplate.from_template(EXPLAIN_PROMPT)
            chain = prompt | cls._llm
            result = await chain.ainvoke({"verse": verse, "lesson_content": lesson_content})
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Erro ao gerar explicacao: {e}"

    @classmethod
    async def generate_quiz(cls, lesson_content: str, count: int = 5, question_type: str = "multiple_choice") -> str:
        if not _LANGCHAIN_AVAILABLE or cls._llm is None:
            return "[]"
        try:
            prompt = ChatPromptTemplate.from_template(QUIZ_PROMPT)
            chain = prompt | cls._llm
            result = await chain.ainvoke({
                "lesson_content": lesson_content,
                "count": count,
                "question_type": question_type,
            })
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f'[]'

    @classmethod
    async def evaluate_open_answer(cls, question: str, answer: str, context: str) -> str:
        if not _LANGCHAIN_AVAILABLE or cls._llm is None:
            return "IA nao disponivel para avaliacao."
        try:
            eval_prompt = ChatPromptTemplate.from_template(
                """Avalie a resposta do aluno para a questao biblica abaixo.
                Questao: {question}
                Resposta do aluno: {answer}
                Contexto da licao: {context}
                Diga se esta correta ou nao, e explique brevemente. Responda em portugues."""
            )
            chain = eval_prompt | cls._llm
            result = await chain.ainvoke({"question": question, "answer": answer, "context": context})
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Erro na avaliacao: {e}"
