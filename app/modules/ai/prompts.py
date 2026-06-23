"""Rótulos e templates de prompt por ação de IA.

Os provedores reais (OpenAI/local) usam `SYSTEM_PROMPT` + `ACTION_INSTRUCTIONS`.
O provedor fake usa apenas `ACTION_LABELS`. O princípio de escopo da Fase 1 está
codificado no SYSTEM_PROMPT: a IA responde SOMENTE com base no documento.
"""

ACTION_LABELS: dict[str, str] = {
    "resumo": "Resumo",
    "pontos_chave": "Pontos Importantes",
    "prazos": "Prazos e Datas",
    "partes": "Partes Envolvidas",
    "valores": "Valores",
    "detalhes": "Análise Detalhada",
    "riscos": "Riscos e Pontos de Atenção",
    "classificacao": "Tipo de Documento",
    "analise_geral": "Análise Geral",
}

SYSTEM_PROMPT = (
    "Você é um assistente jurídico de um Núcleo de Prática Jurídica (NPJ). "
    "Responda SEMPRE em português do Brasil, de forma objetiva e profissional. "
    "Use EXCLUSIVAMENTE as informações contidas no(s) documento(s) fornecido(s). "
    "Se a informação solicitada não constar, diga claramente que não consta no "
    "documento. NUNCA invente fatos, números de processo, leis ou jurisprudência. "
    "Sempre que apresentar prazos ou dados críticos, lembre que devem ser "
    "conferidos por um responsável humano."
)

ACTION_INSTRUCTIONS: dict[str, str] = {
    "resumo": (
        "Faça um resumo objetivo do documento em linguagem clara, destacando o "
        "objeto e as informações essenciais. Use de 1 a 3 parágrafos."
    ),
    "pontos_chave": (
        "Liste, em tópicos, os pontos e trechos mais relevantes do documento "
        "para a análise do caso."
    ),
    "prazos": (
        "Identifique todos os prazos, datas e vencimentos citados no documento. "
        "Para cada um, informe a descrição, a data (se houver) e o trecho de "
        "origem. Avise que os prazos devem ser conferidos por um humano."
    ),
    "partes": (
        "Identifique as partes envolvidas (autor, réu, terceiros etc.), com nome, "
        "papel, qualificação e CPF/CNPJ quando constarem."
    ),
    "valores": (
        "Liste todos os valores monetários, obrigações financeiras, multas e "
        "encargos citados, com a respectiva descrição."
    ),
    "detalhes": (
        "Faça uma análise detalhada do documento, seção a seção (ou cláusula a "
        "cláusula), explicando o conteúdo de cada parte relevante."
    ),
    "riscos": (
        "Aponte cláusulas de risco, pontos de atenção, inconsistências e "
        "possíveis fragilidades identificadas no documento."
    ),
    "classificacao": (
        "Classifique a natureza/tipo do documento e descreva, em uma frase, o "
        "seu objeto. Indique seu grau de confiança (alta/média/baixa)."
    ),
    "analise_geral": (
        "Você receberá vários documentos de um mesmo cliente. Para CADA documento, "
        "informe o tipo/natureza e o que há de mais importante nele. Ao final, "
        "escreva uma visão geral consolidada do conjunto."
    ),
}


def build_user_content(
    action: str,
    document_text: str,
    documents: list[dict] | None = None,
) -> str:
    """Monta o conteúdo da mensagem do usuário para os provedores reais."""
    instruction = ACTION_INSTRUCTIONS.get(action, "Analise o documento.")

    if action == "analise_geral":
        parts = [instruction, ""]
        for i, doc in enumerate(documents or [], start=1):
            parts.append(
                f"=== DOCUMENTO {i}: {doc.get('file_name', 'documento')} "
                f"(tipo: {doc.get('document_type', 'outros')}) ==="
            )
            parts.append(doc.get("text", ""))
            parts.append("")
        return "\n".join(parts)

    return f"{instruction}\n\n=== DOCUMENTO ===\n{document_text}"
