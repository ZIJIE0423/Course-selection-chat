from app.rag.vector_store import get_vector_store


def retrieve_official_docs(query: str, top_k: int = 5):
    vector_store = get_vector_store()
    results = vector_store.similarity_search(
        query,
        k=top_k,
        filter={"source_tier": "tier_2_official_document"},
    )
    return results


def retrieve_student_reviews(query: str, top_k: int = 5):
    vector_store = get_vector_store()
    results = vector_store.similarity_search(
        query,
        k=top_k,
        filter={"source_tier": "tier_3_student_review"},
    )
    return results


def retrieve_all_knowledge(query: str, top_k: int = 8):
    vector_store = get_vector_store()
    results = vector_store.similarity_search(query, k=top_k)
    return results


def retrieve_notices(query: str, top_k: int = 5):
    vector_store = get_vector_store()
    results = vector_store.similarity_search(
        query,
        k=top_k,
        filter={"source_type": "official_notice"},
    )
    return results


def format_rag_evidence(docs) -> str:
    if not docs:
        return "无数据"

    evidence_parts = []
    for i, doc in enumerate(docs):
        meta = doc.metadata
        file_name = meta.get("file_name", "未知文件")
        source_type = meta.get("source_type", "unknown")
        source_url = meta.get("source_url", "")
        is_official = "官方" if meta.get("is_official") else "非官方"

        content_snippet = doc.page_content.replace("\n", " ")[:150] + "..."

        part = f"[{i+1}] 文件名: {file_name} | 类型: {source_type} ({is_official})"
        if source_url:
            part += f" | URL: {source_url}"
        part += f"\n内容摘要: {content_snippet}"
        evidence_parts.append(part)

    return "\n".join(evidence_parts)
