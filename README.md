## 📚 oysj（欧阳思静）


# Wikipedia Clean & Extract Tool

本项目包含两个高性能的 Python 脚本，专为处理从 [Wikipedia dump](https://dumps.wikimedia.org/) 下载的 `.bz2` / `.gz` / `.xml` 数据设计，提供精准清洗和快速提取能力，广泛适用于 NLP 预处理、语料分析、Tokenizer 训练等任务。

---

## ✨ 功能亮点

- ✅ 支持 `.bz2`、`.gz`、普通 `.xml` 输入格式
- 🧹 清洗 `<ref>`、`<math>`、`<table>`、模板 `{{}}` 等结构，保留纯文本内容
- ⚡ 使用 `multiprocessing` 加速处理，每页并发解析
- 📌 支持段落压缩与标题提取
- 📤 可输出结构化纯文本 (`wiki.txt`)
- 📄 附带脚本可提取清洗后前 `N` 行文本（默认2000）

---

## 📦 文件说明

| 文件名        | 功能简介 |
|---------------|-----------|
| `oysj.py` | 主脚本：对 Wikipedia dump 进行清洗、结构化处理，并输出为纯文本文件 |
| `check.py` | 工具脚本：提取清洗后文件的前 2000 行文本，默认写入 `target.txt` |

---

## 🚀 使用方法

### 1️⃣ 清洗 Wikipedia 数据

```bash
python oysj.py --infn enwiki-latest-pages-articles.xml.bz2 --outfn wiki.txt
````

参数说明：

* `--infn`: 输入文件（支持 `.bz2` / `.gz` / `.xml` / `.txt`）
* `--outfn`: 输出清洗后文件（默认：`wiki.txt`）

### 2️⃣ 提取前 2000 行用于模型训练或查看

```bash
python check.py
```

> 默认从 `wiki.txt` 读取，写入前 2000 行到 `target.txt`，可修改源码参数以自定义路径或行数。

---

## 🔧 依赖项

```bash
pip install tqdm
```

> 其余模块为标准库，无需额外安装。

---

## 📚 示例输出格式

```text
Python (programming language):
Python is a high-level, general-purpose programming language. ...
It was created by Guido van Rossum and first released in 1991.
...

Artificial intelligence:
Artificial intelligence (AI) is intelligence demonstrated by machines...
```

---

## 💡 应用场景

* 预训练语言模型（如 BERT、GPT）
* Tokenizer/BPE 模型训练
* 文本分类、命名实体识别等 NLP 任务预处理
* 中文或多语言语料分析

---

## 📄 License

MIT License

---

## 🙋‍♂️ 作者

欢迎 Issues 和 PR！如有建议、问题或优化想法，欢迎交流。





#ENGLISH version

# Wikipedia Clean & Extract Tool

This project provides two high-performance Python scripts designed for cleaning and extracting Wikipedia dump files (`.bz2`, `.gz`, `.xml`). It aims to remove irrelevant or noisy content such as references, templates, footnotes, tables, etc., and retain only clean, structured text suitable for NLP tasks like tokenizer training or language model pretraining.

---

## ✨ Features

- ✅ Supports `.bz2`, `.gz`, and uncompressed `.xml` files
- 🧹 Removes `<ref>`, `<math>`, `<table>`, templates (`{{}}`), HTML tags, and more
- ⚡ Fast multi-core processing using Python's `multiprocessing`
- 📌 Collapses and compresses sections into meaningful paragraphs
- 📤 Outputs clean structured text to a single `.txt` file (`wiki.txt`)
- 📄 Comes with a utility script to extract the first N lines (default: 2000 lines) from the cleaned output

---

## 📁 Files

| Filename         | Description |
|------------------|-------------|
| `oysj.py`  | Main script for cleaning and extracting Wikipedia XML dump content |
| `check.py` | Helper script to extract the first N lines from the cleaned text |

---

## 🚀 Usage

### 1️⃣ Clean the Wikipedia dump file

```bash
python oysj.py --infn enwiki-latest-pages-articles.xml.bz2 --outfn wiki.txt
````

Arguments:

* `--infn`: Input file path (`.bz2`, `.gz`, `.xml`, or `.txt`)
* `--outfn`: Output text file after cleaning (default: `wiki.txt`)

### 2️⃣ Extract the first 2000 lines for preview or tokenizer training

```bash
python check.py
```

> By default, it reads from `wiki.txt` and writes the first 2000 lines into `target.txt`. You can modify the parameters inside the script to customize the input/output path or line count.

---

## 🔧 Dependencies

```bash
pip install tqdm
```

All other modules are from Python's standard library.

---

## 📄 Sample Output

```text
Python (programming language):
Python is a high-level, general-purpose programming language. ...
It was created by Guido van Rossum and first released in 1991.
...

Artificial intelligence:
Artificial intelligence (AI) is intelligence demonstrated by machines...
```

---

## 💡 Use Cases

* Pretraining datasets for large language models (e.g., BERT, GPT)
* Custom tokenizer training (BPE, WordPiece, etc.)
* NLP corpus generation and filtering
* Language analysis, multilingual text processing

---

## 📜 License

MIT License

---

## 🙋‍♂️ Author

Feel free to open an issue or pull request if you have suggestions, questions, or improvements. Contributions are welcome!

---



