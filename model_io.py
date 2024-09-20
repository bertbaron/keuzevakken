from excel_exporter import ExcelExporter
from excel_loader import ExcelLoader
from model import Data


def load(file_path: str, previous: str | None) -> Data:
    loader = ExcelLoader(file_path, previous)
    data = loader.load()
    data.validate()
    return data


def write_to_excel(data: Data, path: str):
    exporter = ExcelExporter()
    exporter.export(data, path)
