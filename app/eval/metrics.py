import json

def calculate_route_accuracy(results):
    correct = sum(1 for r in results if r["predicted_route"] == r["expected_route"])
    return correct / len(results) if results else 0

def calculate_source_type_accuracy(results):
    correct = sum(1 for r in results if r["predicted_source_type"] == r["expected_source_type"])
    return correct / len(results) if results else 0

def calculate_abstain_accuracy(results):
    # should_abstain=True means it should decline. 
    # we consider it declined if "未找到", "未检索到", "不足" is in the answer.
    correct = 0
    for r in results:
        is_abstained = any(kw in r["answer"] for kw in ["未找到", "未检索到", "不足", "没有找到"])
        if r["should_abstain"] == is_abstained:
            correct += 1
    return correct / len(results) if results else 0

def calculate_citation_coverage(results):
    # Check if the answer cites the source type correctly based on the prompt policies
    # "根据课程结构化数据库查询结果", "官方文档", "学生评价仅作为非官方参考" etc.
    correct = 0
    for r in results:
        if r["predicted_source_type"] == "official_structured_db":
            if "来源" in r["answer"] or "数据库" in r["answer"] or "未找到" in r["answer"]:
                correct += 1
        elif r["predicted_source_type"] == "official_document_rag":
            if "来源" in r["answer"] or "官方" in r["answer"] or "未找到" in r["answer"]:
                correct += 1
        elif r["predicted_source_type"] == "student_review_rag":
            if "来源" in r["answer"] or "非官方" in r["answer"] or "评价" in r["answer"] or "未找到" in r["answer"]:
                correct += 1
        elif r["predicted_source_type"] == "hybrid":
            if "来源" in r["answer"] or ("官方" in r["answer"] and "评价" in r["answer"]) or "未找到" in r["answer"]:
                correct += 1
        else:
            # fallback or unknown
            if "未找到" in r["answer"]:
                correct += 1
    return correct / len(results) if results else 0

def calculate_hallucination_flag(results):
    # A hallucination occurs if it shouldn't abstain but didn't find info and made it up,
    # or if it should abstain but gave a confident answer without abstain keywords.
    hallucinated = 0
    for r in results:
        is_abstained = any(kw in r["answer"] for kw in ["未找到", "未检索到", "不足", "没有找到"])
        if r["should_abstain"] and not is_abstained:
            hallucinated += 1
    return hallucinated / len(results) if results else 0

def calculate_keyword_hit_rate(results):
    hit_rates = []
    for r in results:
        keywords = r["gold_answer_keywords"]
        if not keywords:
            hit_rates.append(1.0)
            continue
        hits = sum(1 for kw in keywords if kw in r["answer"])
        hit_rates.append(hits / len(keywords))
    return sum(hit_rates) / len(hit_rates) if hit_rates else 0

def calculate_tool_usage_accuracy(results):
    # simplified mapping
    expected_tools_map = {
        "mysql_query": ["mysql_query"],
        "official_doc_rag": ["retrieve_official_docs"],
        "student_review_rag": ["retrieve_student_reviews"],
        "hybrid_sql_rag": ["mysql_query", "retrieve_student_reviews"]
    }
    
    correct = 0
    for r in results:
        expected = expected_tools_map.get(r["expected_route"], [])
        used = r.get("used_tools", [])
        if set(expected) == set(used) or (not expected and not used):
            correct += 1
    return correct / len(results) if results else 0

def calculate_all_metrics(results):
    return {
        "route_accuracy": calculate_route_accuracy(results),
        "source_type_accuracy": calculate_source_type_accuracy(results),
        "abstain_accuracy": calculate_abstain_accuracy(results),
        "citation_coverage": calculate_citation_coverage(results),
        "hallucination_flag": calculate_hallucination_flag(results),
        "keyword_hit_rate": calculate_keyword_hit_rate(results),
        "tool_usage_accuracy": calculate_tool_usage_accuracy(results),
        "faithfulness_score": None, # 预留 RAGAS
        "context_precision_score": None # 预留 RAGAS
    }
