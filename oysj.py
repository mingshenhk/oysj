import os
import re
import bz2
import gzip
import io
import sys
import mimetypes
from multiprocessing import Pool, cpu_count
from tqdm import tqdm



# ---------- 参数设置 ----------
keepLinks = False
acceptedNamespaces = set(['w'])
discardElements = set([
    'gallery', 'timeline', 'noinclude', 'pre',
    'table', 'tr', 'td', 'th', 'caption',
    'form', 'input', 'select', 'option', 'textarea',
    'ul', 'li', 'ol', 'dl', 'dt', 'dd', 'menu', 'dir',
    'ref', 'references', 'img', 'imagemap', 'source'
])
# ---------- 正则预编译 ----------
comment_re = re.compile(r'<!--.*?-->', re.DOTALL)
preformatted_re = re.compile(r'^ .*?$', re.MULTILINE)
external_link_re = re.compile(r'\[\w+.*? (.*?)\]')
external_link_no_anchor_re = re.compile(r'\[\w+[&\]]*\]')
bold_italic_re = re.compile(r"'''''([^']*?)'''''")
bold_re = re.compile(r"'''(.*?)'''")
italic_quote_re = re.compile(r"''\"(.*?)\"''")
italic_re = re.compile(r"''([^']*)''")
quote_quote_re = re.compile(r'""(.*?)""')
spaces_re = re.compile(r' {2,}')
dots_re = re.compile(r'\.{4,}')
section_re = re.compile(r'(==+)\s*(.*?)\s*\1')
tag_re = re.compile(r'(.*?)<(/?\w+)[^>]*>(?:([^<]*)(<.*?>)?)?')
parametrized_link_re = re.compile(r'\[\[.*?\]\]')
wiki_link_re = re.compile(r'\[\[([^[]*?)(?:\|([^[]*?))?\]\](\w*)')
special_token_re = re.compile(r"__[A-Z]+__")
html_entities_re = re.compile("&#?(\w+);")

discard_combined_re = re.compile(
    r'<({})\b[^>]*>.*?</\1>'.format('|'.join(discardElements)),
    re.DOTALL | re.IGNORECASE
)

# ---------- HTML Entity 替换 ----------
from html.entities import name2codepoint

def unescape(text):
    def fixup(m):
        code = m.group(1)
        try:
            if code.startswith('#x'):
                return chr(int(code[2:], 16))
            elif code.startswith('#'):
                return chr(int(code[1:]))
            else:
                return chr(name2codepoint[code])
        except:
            return m.group(0)
    return html_entities_re.sub(fixup, text)

# ---------- Wiki 链接处理 ----------
def make_anchor_tag(match):
    link = match.group(1)
    colon = link.find(':')
    if colon > 0 and link[:colon] not in acceptedNamespaces:
        return ''
    trail = match.group(3)
    anchor = match.group(2) or link
    anchor += trail
    return '<a href="%s">%s</a>' % (link, anchor) if keepLinks else anchor

# ---------- 清理函数 ----------
def clean(text):
    import re
    from html import unescape

    for _ in range(10):  # 多轮逼近嵌套结构
        # 清除 <ref name="..." /> 形式（自闭合）
        text = re.sub(r'<ref\s+[^>]*?/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[\(（]\s*<math\b[^>]*?>.*?</math>\s*[\)）]', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<math\b[^>]*?>.*?</math>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<references\b[^<>]*?\/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<references\b[^<>]*?/?>', '', text, flags=re.IGNORECASE)

        # 清除 <ref>...</ref> 或 <ref name="...">...</ref>
        text = re.sub(r'<ref\b[^>]*?>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<ref[^>]*?>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ref>', '', text, flags=re.IGNORECASE)
        # 清除 references 块和残留结构
        text = re.sub(r'<references\b[^<>]*/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<references\b[^<>]*?>.*?</references>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<div[^>]*?class=["\']?references-[^>]*?>\s*</div>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*references\b[^<>]*?\/\s*>', '', text, flags=re.IGNORECASE)

    for _ in range(3):
        text = re.sub(r'<\s*references\b[^<>]*?\/\s*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*references\b[^<>]*?>.*?<\s*/\s*references\s*>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<div[^>]*?class=["\']?references-[^>]*?>\s*</div>', '', text, flags=re.IGNORECASE)

    for _ in range(3):
        # 自闭合 <ref name="..." />
        text = re.sub(r'<ref\s+[^>]*?/>', '', text, flags=re.IGNORECASE)
    
        # 普通 <ref>...</ref>，含 name 属性或无属性
        text = re.sub(r'<ref\b[^>]*?>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 兜底清理残余 <ref>（未闭合或异常格式）
        text = re.sub(r'<ref[^>]*?>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ref>', '', text, flags=re.IGNORECASE)

    # 多轮清洗结构标签（处理嵌套 + 连续标签）
    for _ in range(3):
        # 引用与脚注（<ref ... />、<ref>...</ref>）
        text = re.sub(r'<ref\s+name\s*=\s*["\'][^"\']+["\']\s*/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<ref\b[^<>]*?/?>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<ref\b[^<>]*?/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<ref\b[^<>]*?>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<ref[^>]*?>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ref>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<cite\b[^>]*?>.*?</cite>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<span[^>]*class=["\']?citation[^>]*?>.*?</span>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<div[^>]*class=["\']?citation[^>]*?>.*?</div>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<footnote\b[^>]*?>.*?</footnote>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<footnoteref\b[^>]*?/?>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<a[^>]+id=["\']cite_ref-[^"\']+["\'][^>]*?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<a[^>]+href=["\']#cite_note[^>]*?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\[edit\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[source\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[note \d+\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]*class=["\']?mw-cite[^>]*?>.*?</[^>]+>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]*class=["\']?reference-text[^>]*?>.*?</[^>]+>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<table[^>]*class=["\']?references[^>]*?>.*?</table>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<table[^>]*class=["\']?citation[^>]*?>.*?</table>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+data-cite[^>]*?>.*?</[^>]+>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+data-note[^>]*?>.*?</[^>]+>', '', text, flags=re.IGNORECASE | re.DOTALL)


        text = re.sub(r'<references\b[^<>]*/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<references\b[^<>]*?>.*?</references>', '', text, flags=re.DOTALL | re.IGNORECASE)

        text = re.sub(r'<div[^>]*class=["\']?references-[^>]*?>\s*</div>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<div[^>]*class=["\']?references[^>]*?>.*?</div>', '', text, flags=re.IGNORECASE | re.DOTALL)

        text = re.sub(r'<span[^>]*class=["\']?mw-references-wrap[^>]*?>.*?</span>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<span[^>]*class=["\']?references[^>]*?>.*?</span>', '', text, flags=re.IGNORECASE | re.DOTALL)

        text = re.sub(r'<ol[^>]*class=["\']?references[^>]*?>.*?</ol>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<ul[^>]*class=["\']?references[^>]*?>.*?</ul>', '', text, flags=re.IGNORECASE | re.DOTALL)

        text = re.sub(r'<li[^>]+id=["\']cite_note[^>]*?>.*?</li>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<li[^>]*class=["\']?reference[^>]*?>.*?</li>', '', text, flags=re.IGNORECASE | re.DOTALL)

        text = re.sub(r'<sup[^>]+class=["\']?reference[^>]*?>.*?</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<sup[^>]*?>\[\d+\]</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<sup[^>]*?>\d+</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<sup[^>]*?>.*?</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # 数学公式
        text = re.sub(r'<math\b[^>]*?>.*?</math>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 模板结构 {{...}} 与表格 {|...|}
        text = re.sub(r'\{\{[^{}]*?\}\}', '', text, flags=re.DOTALL)
        text = re.sub(r'\{\|[^{}]*?\|\}', '', text, flags=re.DOTALL)

    # 特殊结构
    text = re.sub(r'-\{[^\{\}]*?\}-', '', text)  # zh-hant:zh-hans
    text = re.sub(r'^\s*[\u4e00-\u9fffA-Za-z0-9·—\-（）()\[\]“”‘’\'":：]+?\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'（，[^）]*?）', '', text)

    # 删除 sub、sup 标签内容
    text = re.sub(r'<sub>.*?</sub>', '', text, flags=re.DOTALL)
    text = re.sub(r'<sup>.*?</sup>', '', text, flags=re.DOTALL)

    # 空括号与空引号
    for pair in [
        r'\(\s*\)', r'（\s*）', r'\[\s*\]', r'【\s*】', r'\{\s*\}', r'｛\s*｝',
        r'<\s*>', r'《\s*》', r'""', r"''", r'“\s*”', r'‘\s*’'
    ]:
        text = re.sub(pair, '', text)
    text = re.sub(r'<(div|p|span)[^>]*?>\s*</\1>', '', text, flags=re.IGNORECASE)

    # Wiki 链接结构
    text = wiki_link_re.sub(make_anchor_tag, text)
    text = parametrized_link_re.sub('', text)

    # 外链与强调语法
    text = external_link_re.sub(r'\1', text)
    text = external_link_no_anchor_re.sub('', text)
    text = bold_italic_re.sub(r'\1', text)
    text = bold_re.sub(r'\1', text)
    text = italic_quote_re.sub(r'&quot;\1&quot;', text)
    text = italic_re.sub(r'&quot;\1&quot;', text)
    text = quote_quote_re.sub(r'\1', text)
    text = text.replace("'''", '').replace("''", '&quot;')

    # HTML 实体与注释
    text = unescape(unescape(text))
    text = comment_re.sub('', text)
    text = discard_combined_re.sub('', text)
    text = preformatted_re.sub('', text)

    # 空白与重复符号
    text = text.replace('\t', ' ')
    text = spaces_re.sub(' ', text)
    text = dots_re.sub('...', text)
    text = re.sub(' (,:\.\)\»)', r'\1', text)
    text = re.sub('(\[\(\«) ', r'\1', text)
    text = re.sub(r'\n\W+?\n', '\n', text)
    text = text.replace(',,', ',').replace(',.', '.')
    text = special_token_re.sub("", text)

    # 表格残留符号
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(span|font|div|small|center|big|bdi|u|s|tt|code|kbd|mark|ruby|rp|rt|var|bdo)[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*\|\}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\|\-\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*!\s*.*$', '', text, flags=re.MULTILINE)

    # 模板参数与特殊模块
    text = re.sub(r'\{\{\{[^{}]*?\}\}\}', '', text)
    text = re.sub(r'\{\{#(invoke|if|expr):.*?\}\}', '', text, flags=re.DOTALL)

    # 文件、分类、模板、控制指令
    text = re.sub(r'\[\[(File|Image):[^\[\]]*?\]\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\[(Category|Template):[^\[\]]*?\]\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'__\w+__', '', text)

    # Markdown 与编辑痕迹
    text = re.sub(r"'{2,5}", '', text)
    text = re.sub(r'~~+', '', text)
    text = re.sub(r'__[^_]+__', '', text)

    # 文献编号与标注
    text = re.sub(r'\[\d{1,3}\]', '', text)
    text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[dead link\]', '', text, flags=re.IGNORECASE)

    # 表格符号
    text = re.sub(r'\|\|+', ' ', text)
    text = re.sub(r'!!+', ' ', text)

    # 模板语言标记
    text = re.sub(r'\{\{lang-[a-z\-]+?\|([^{}|]+?)\}\}', r'\1', text)
    text = re.sub(r'\{\{transl-[a-z\-]+?\|[^|]+\|([^{}|]+?)\}\}', r'\1', text)
    text = re.sub(r'<ref\s+name\s*=\s*["\'][^"\']+["\']\s*/>', '', text, flags=re.IGNORECASE)


    # 特殊注释
    text = re.sub(r'<!--T:\d+-->', '', text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # 下划线替代空格
    text = re.sub(r'(?<=\w)_(?=\w)', ' ', text)

    # 控制字符与 Unicode 空格
    text = text.replace('\u00a0', ' ')
    text = text.replace('\u200b', '')
    text = text.replace('\u202f', ' ')
    text = text.replace('\u200e', '')

    # Emoji 表情符号移除
    text = re.sub(
        r'[\U0001F300-\U0001F5FF'
        r'\U0001F600-\U0001F64F'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F700-\U0001F77F'
        r'\U0001F780-\U0001F7FF'
        r'\U0001F800-\U0001F8FF'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F'
        r'\U0001FA70-\U0001FAFF'
        r'\U00002702-\U000027B0]+', '', text
    )

    return text




# ---------- 段落压缩 ----------
def compact(text):
    page = []
    headers = {}
    empty_section = False

    for line in text.split('\n'):
        if not line:
            continue
        m = section_re.match(line)
        if m:
            title = m.group(2)
            if title and title[-1] not in '!?':
                title += '.'
            headers[len(m.group(1))] = title
            empty_section = True
            continue
        if line.startswith('++'):
            title = line[2:-2]
            if title and title[-1] not in '!?':
                title += '.'
            page.append(title)
        elif line[0] in '*#:;{|' or line[-1] in '}':
            continue
        elif (line[0] == '(' and line[-1] == ')') or line.strip('.-') == '':
            continue
        elif headers:
            for _, v in sorted(headers.items()):
                page.append(v)
            headers.clear()
            page.append(line)
            empty_section = False
        elif not empty_section:
            page.append(line)
    return page

# ---------- 文档生成 ----------
def generate_document(page_id, title, text):
    text = clean(text)
    return f'\n{title}:' + '\n' + '\n'.join(compact(text)) + '\n'

# ---------- 分割 <page> 块 ----------
def split_pages(text):
    return re.findall(r'<page>.*?</page>', text, re.DOTALL)

# ---------- 每页处理 ----------
def process_page_block(block):
    id_match = re.search(r'<id>(\d+)</id>', block)
    title_match = re.search(r'<title>(.*?)</title>', block)
    text_match = re.search(r'<text[^>]*>(.*?)</text>', block, re.DOTALL)

    if not (id_match and title_match and text_match):
        return ''

    page_id = id_match.group(1)
    title = title_match.group(1)
    text = text_match.group(1)

    if ':' in title and title.split(':')[0] not in acceptedNamespaces:
        return ''
    if '<redirect' in block:
        return ''

    return generate_document(page_id, title, text)

# ---------- 主函数 ----------
def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--infn', type=str, required=True)
    parser.add_argument('--outfn', type=str, default='wiki.txt')
    args = parser.parse_args()

    fname = args.infn
    outfn = args.outfn

    if not os.path.exists(fname):
        print(f"File not found: {fname}")
        sys.exit(1)

    ftypes = mimetypes.guess_type(fname)
    if 'bzip2' in ftypes:
        with bz2.open(fname, mode='rt', encoding='utf-8') as f:
            raw = f.read()
    elif 'gzip' in ftypes:
        with gzip.open(fname, mode='rt', encoding='utf-8') as f:
            raw = f.read()
    else:
        with open(fname, 'r', encoding='utf-8') as f:
            raw = f.read()

    pages = split_pages(raw)
    print(f"Total pages: {len(pages)}")

    with Pool(processes=cpu_count()) as pool:
        with open(outfn, 'w', encoding='utf-8', buffering=1024 * 1024) as outf:
            for result in tqdm(pool.imap(process_page_block, pages, chunksize=32), total=len(pages)):
                if result:
                    outf.write(result)

if __name__ == '__main__':
    main()
