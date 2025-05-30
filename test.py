import pandas as pd
# import matplotlib.pyplot as plt
import dataframe_image as dfi

# 1. 生成简单的表格 markdown 数据
markdown = '''
| Name   | Age | Score |
|--------|-----|-------|
| Alice  | 23  | 88    |
| Bob    | 25  | 92    |
| Carol  | 22  | 95    |
'''

# 2. 解析 markdown 为 DataFrame
from io import StringIO
import re

def markdown_to_df(md):
    lines = [line.strip() for line in md.strip().split('\n') if line.strip()]
    # 跳过分隔线
    lines = [line for i, line in enumerate(lines) if i != 1]
    csv_str = '\n'.join([re.sub(r'\s*\|\s*', ',', line.strip('| ')) for line in lines])
    df = pd.read_csv(StringIO(csv_str))
    return df

df = markdown_to_df(markdown)

# 让表格内容和表头都居中
styled_df = df.style.set_table_styles(
    [
        {'selector': 'th', 'props': [('text-align', 'center')]},
        {'selector': 'td', 'props': [('text-align', 'center')]}
    ]
).set_properties(**{'text-align': 'center'})

dfi.export(
    styled_df,
    'output/markdown_table.png',
    table_conversion='matplotlib',
    fontsize=24,  # 设置字体大小
    max_rows=10,
    max_cols=10
)
print("表格图片已保存到: output/markdown_table.png")
