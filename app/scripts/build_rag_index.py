import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.rag.document_loader import load_all_documents
from app.rag.text_splitter import split_documents
from app.rag.vector_store import add_documents_to_store, clear_vector_store

def main():
    parser = argparse.ArgumentParser(description="构建 RAG 知识库索引")
    parser.add_argument("--rebuild", action="store_true", help="清空旧索引后重建")
    args = parser.parse_args()

    data_dirs = [project_root / '数据文件', project_root / 'demo_data' / 'm1_synthetic' / 'knowledge']
    
    if args.rebuild:
        print("清理旧的 ChromaDB 索引...")
        clear_vector_store()
        
    print("正在读取基础资料与 M1 合成补充资料...")
    docs = []
    for data_dir in data_dirs:
        if data_dir.exists():
            docs.extend(load_all_documents(data_dir))
    
    if not docs:
        print("未找到需要处理的文档。")
        return
        
    print(f"成功读取 {len(docs)} 个文件。开始进行文本切分...")
    split_docs = split_documents(docs)
    
    print(f"切分完成，共生成 {len(split_docs)} 个 chunk。开始写入向量数据库...")
    try:
        add_documents_to_store(split_docs)
        print("写入成功！")
    except Exception as e:
        print(f"写入失败: {e}")

    print("\n=== 构建统计 ===")
    print(f"读取文件数: {len(docs)}")
    print(f"生成 chunk 数: {len(split_docs)}")
    print("================\n")

if __name__ == "__main__":
    main()
