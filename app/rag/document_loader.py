import os
from pathlib import Path

def get_source_info(filename: str):
    """根据文件名获取 source_type, source_tier 和 is_official"""
    if "培养方案" in filename:
        return "official_programme_plan", "tier_2_official_document", True
    elif "选课指导" in filename:
        return "official_selection_guide", "tier_2_official_document", True
    elif "选课评价参考" in filename:
        return "student_review", "tier_3_student_review", False
    else:
        return "unknown", "tier_4_unknown", False

def load_markdown_file(filepath: Path):
    """读取 Markdown 文件，返回文件内容和基础元数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    source_type, source_tier, is_official = get_source_info(filepath.name)
    
    metadata = {
        "file_name": filepath.name,
        "source_type": source_type,
        "source_tier": source_tier,
        "is_official": is_official
    }
    
    return content, metadata

def load_all_documents(data_dir: Path):
    """加载目录下所有 .md 文件"""
    docs = []
    for file in data_dir.glob("*.md"):
        # 跳过结构化数据，因为它已经导入到 MySQL
        if "结构化数据" in file.name:
            continue
        content, metadata = load_markdown_file(file)
        docs.append((content, metadata))
    return docs
