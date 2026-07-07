"""Indicizzatore statico del codice Python basato su ast."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from services.knowledge_graph.models import KnowledgeEdge, KnowledgeGraphSnapshot, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore


class PythonCodeIndexer:
    """Scansiona file Python e crea nodi/relazioni Graphify-ready."""

    IGNORED_DIRECTORIES = {".git", "__pycache__", ".venv", "venv", "data", "logs"}

    def __init__(self, repository_root: str | Path = "."):
        self.repository_root = Path(repository_root).resolve()

    def index_repository(self, store: KnowledgeGraphStore | None = None) -> KnowledgeGraphSnapshot:
        """Indicizza tutti i file Python del repository nello store indicato."""
        target_store = store or KnowledgeGraphStore()
        for file_path in self._iter_python_files():
            self._index_file(file_path, target_store)
        return target_store.get_snapshot()

    def build_snapshot(self) -> KnowledgeGraphSnapshot:
        """Crea uno snapshot in memoria senza scrivere su disco."""
        store = KnowledgeGraphStore(path=self.repository_root / ".knowledge_graph_index_tmp.json")
        return self.index_repository(store)

    def _iter_python_files(self) -> Iterable[Path]:
        for path in sorted(self.repository_root.rglob("*.py")):
            relative_parts = path.relative_to(self.repository_root).parts
            if any(part in self.IGNORED_DIRECTORIES for part in relative_parts):
                continue
            yield path

    def _index_file(self, file_path: Path, store: KnowledgeGraphStore) -> None:
        relative_path = file_path.relative_to(self.repository_root).as_posix()
        file_id = f"python_file:{relative_path}"
        store.upsert_node(KnowledgeNode(
            id=file_id,
            type="python_file",
            label=relative_path,
            properties={"path": relative_path},
        ))

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relative_path)
        except (SyntaxError, UnicodeDecodeError) as exc:
            store.upsert_node(KnowledgeNode(
                id=file_id,
                type="python_file",
                label=relative_path,
                properties={"path": relative_path, "parse_error": str(exc)},
            ))
            return

        visitor = _CodeGraphVisitor(store=store, file_id=file_id, relative_path=relative_path)
        visitor.visit(tree)


class _CodeGraphVisitor(ast.NodeVisitor):
    def __init__(self, store: KnowledgeGraphStore, file_id: str, relative_path: str):
        self.store = store
        self.file_id = file_id
        self.relative_path = relative_path
        self.scope_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = self._qualname(node.name)
        class_id = f"python_class:{self.relative_path}:{class_name}"
        parent_id = self.scope_stack[-1] if self.scope_stack else self.file_id
        self.store.upsert_node(KnowledgeNode(
            id=class_id,
            type="python_class",
            label=node.name,
            properties={
                "file": self.relative_path,
                "qualname": class_name,
                "line": node.lineno,
            },
        ))
        self.store.upsert_edge(KnowledgeEdge(
            source=parent_id,
            target=class_id,
            relationship="CONTAINS",
            properties={"line": node.lineno},
        ))
        self.scope_stack.append(class_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add_import(module=alias.name, imported_name=alias.asname or alias.name, line=node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * int(node.level or 0) + (node.module or "")
        for alias in node.names:
            imported_name = alias.asname or alias.name
            import_label = f"{module}.{alias.name}".strip(".")
            self._add_import(module=module or ".", imported_name=imported_name, line=node.lineno, label=import_label)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        function_name = self._qualname(node.name)
        function_id = f"python_function:{self.relative_path}:{function_name}"
        parent_id = self.scope_stack[-1] if self.scope_stack else self.file_id
        self.store.upsert_node(KnowledgeNode(
            id=function_id,
            type="python_function",
            label=node.name,
            properties={
                "file": self.relative_path,
                "qualname": function_name,
                "line": node.lineno,
                "async": is_async,
            },
        ))
        self.store.upsert_edge(KnowledgeEdge(
            source=parent_id,
            target=function_id,
            relationship="CONTAINS",
            properties={"line": node.lineno},
        ))
        self.scope_stack.append(function_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def _add_import(self, module: str, imported_name: str, line: int, label: str | None = None) -> None:
        clean_label = label or module
        import_id = f"python_import:{clean_label}"
        self.store.upsert_node(KnowledgeNode(
            id=import_id,
            type="python_import",
            label=clean_label,
            properties={"module": module, "imported_name": imported_name},
        ))
        self.store.upsert_edge(KnowledgeEdge(
            source=self.file_id,
            target=import_id,
            relationship="IMPORTS",
            properties={"line": line, "imported_name": imported_name},
        ))

    def _qualname(self, name: str) -> str:
        if not self.scope_stack:
            return name
        parent = self.scope_stack[-1].split(":", 2)[-1]
        return f"{parent}.{name}"
