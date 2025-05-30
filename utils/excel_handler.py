import xlwings as xw
import os

class ExcelHandler:
    def __init__(self, filepath, sheet_name):
        self.filepath = filepath
        self.sheet_name = sheet_name

    # 写入数据到指定单元格
    # data: {字段名: 值}
    # cell_map: {字段名: 单元格，如 'A1'}
    def write_data(self, data, cell_map):
        app = xw.App(visible=False, add_book=False)
        try:
            wb = app.books.open(self.filepath)
            ws = wb.sheets[self.sheet_name]
            for key, value in data.items():
                cell = cell_map.get(key)
                if cell:
                    # 兼容 value 可能是 dict（如 {'default': 0, ...}）
                    if isinstance(value, dict) and 'default' in value:
                        ws.range(cell).value = value['default']
                    else:
                        ws.range(cell).value = value
                    print(f"写入 {key} 到 {cell}: {value}")
            wb.save()
            wb.close()
        except Exception as e:
            print(f"[ERROR] 保存Excel文件失败: {self.filepath}, 错误: {e}")
            raise RuntimeError(f"保存Excel文件失败: {self.filepath}, 错误: {e}")
        finally:
            app.quit()

    # 循环读取刚刚写入的数据，验证是否成功
    def read_written_data(self, cell_map):
        app = xw.App(visible=False, add_book=False)
        result = {}
        try:
            wb = app.books.open(self.filepath)
            ws = wb.sheets[self.sheet_name]
            for key, cell in cell_map.items():
                result[key] = ws.range(cell).value
                print(f"读取 {key} 从 {cell}: {result[key]}")
            wb.close()
        except Exception as e:
            print(f"[ERROR] 读取Excel文件失败: {self.filepath}, 错误: {e}")
            raise RuntimeError(f"读取Excel文件失败: {self.filepath}, 错误: {e}")
        finally:
            app.quit()
        return result

    # 读取指定单元格的数据
    # cell_map: {字段名: 单元格，如 'B5'}
    def read_data(self, cell_map):
        return self.read_written_data(cell_map)
