
# PDF Studio Android 📄

A powerful, all-in-one PDF and image utility application built with Python and Kivy, specifically designed for Android and cross-platform use.

**PDF Studio** allows users to manipulate PDF documents, convert images, and manage metadata through a modern, responsive interface.

---

## ✨ Features

- **Merge PDFs**: Combine multiple PDF documents into a single file.
- **Split PDFs**: Extract specific pages or split a large PDF into individual files.
- **Images to PDF**: Convert collections of images into high-quality PDF documents.
- **PDF to Images**: Export PDF pages as separate image files.
- **Watermarking**: Protect your documents with customizable text watermarks.
- **Metadata Editor**: View and edit PDF metadata (Author, Title, Subject, Keywords).
- **Password Protection**: Secure your documents with PDF encryption.
- **Android Optimized**: Full integration with Android's Storage Access Framework (SAF) for secure file handling.

---

## 🛠️ Technical Stack

- **Framework**: Kivy  
- **PDF Logic**: pypdf, reportlab  
- **Image Processing**: Pillow (PIL), numpy  
- **Platform Integration**: Pyjnius / Android Storage Access Framework (SAF)

---

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Kivy & KivyMD
- Pillow
- pypdf
- reportlab

---

### Setup

#### Clone the repository:

```bash
git clone https://github.com/FarazAli30/pdf-studio-android.git
cd pdf-studio-android
````

#### Install dependencies:

```bash
pip install -r requirements.txt
```

#### Run the application:

```bash
python main.py
```

---

## 📱 Android Deployment

This app is optimized for Android using **Buildozer**.

### Steps to compile APK:

1. Install Buildozer.
2. Ensure you have the following requirements in your `buildozer.spec`:

```txt
requirements = python3,kivy,pypdf,reportlab,pillow,numpy,android,pyjnius
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
```

3. Run:

```bash
buildozer android debug deploy run
```

---

## 🤝 Contributing

Contributions are welcome!
Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License – see the `LICENSE` file for details.

