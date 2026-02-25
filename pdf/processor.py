"""
processor.py
------------
PDFProcessor — all PDF manipulation logic lives here.
Completely decoupled from Kivy UI (uses App.get_running_app() only for
user_data_dir). Each method returns (success: bool, path: str|None, msg: str).
"""

import os
import io
import logging
import shutil
import zipfile
from datetime import datetime

import numpy as np
from PIL import Image
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject, NumberObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import grey
from kivy.app import App


class PDFProcessor:

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_save_path(original_path, prefix, ext=".pdf"):
        app_dir = App.get_running_app().user_data_dir
        ts = datetime.now().strftime("%H%M%S")
        base_name = "doc"
        if original_path and os.path.exists(original_path):
            base_name = os.path.splitext(os.path.basename(original_path))[0]
        return os.path.join(app_dir, f"{prefix}_{base_name}_{ts}{ext}")

    # ── Compress ──────────────────────────────────────────────────────────────

    @staticmethod
    def compress_pdf_working(input_path, output_path, scale_factor=0.5,
                              quality=60, progress_callback=None):
        try:
            logging.info(f"Compressing: {input_path} -> {output_path}")
            reader = PdfReader(input_path)
            writer = PdfWriter()
            images_processed = 0
            images_failed = 0

            resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
            total = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback((page_num + 1) / total * 100)
                writer.add_page(page)
                w_page = writer.pages[page_num]

                if "/Resources" in w_page and "/XObject" in w_page["/Resources"]:
                    xobjects = w_page["/Resources"]["/XObject"]
                    if hasattr(xobjects, "get_object"):
                        xobjects = xobjects.get_object()
                    for obj_name in list(xobjects.keys()):
                        obj = xobjects[obj_name]
                        if hasattr(obj, "get_object"):
                            obj = obj.get_object()
                        if obj.get("/Subtype") != "/Image":
                            continue
                        try:
                            width  = int(obj["/Width"])
                            height = int(obj["/Height"])
                            data   = obj.get_data()
                            cs     = obj.get("/ColorSpace", "/DeviceRGB")
                            if hasattr(cs, "get_object"):
                                cs = cs.get_object()
                            cs_str = str(cs)
                            if "Gray" in cs_str or cs == "/DeviceGray":
                                mode, ch = "L", 1
                            elif "CMYK" in cs_str or cs == "/DeviceCMYK":
                                mode, ch = "CMYK", 4
                            else:
                                mode, ch = "RGB", 3

                            img = None
                            try:
                                if len(data) == width * height * ch:
                                    img = Image.frombytes(mode, (width, height), data)
                                else:
                                    arr = np.frombuffer(data, dtype=np.uint8)
                                    if ch == 3 and len(arr) >= width * height * 3:
                                        img = Image.fromarray(arr[:width*height*3].reshape(height, width, 3), "RGB")
                                    elif ch == 1 and len(arr) >= width * height:
                                        img = Image.fromarray(arr[:width*height].reshape(height, width), "L")
                            except Exception:
                                images_failed += 1
                                continue

                            if img is None:
                                continue

                            nw = max(1, int(width  * scale_factor))
                            nh = max(1, int(height * scale_factor))
                            img = img.resize((nw, nh), resample)
                            if img.mode == "CMYK":
                                img = img.convert("RGB")

                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=int(quality), optimize=True)
                            cdata = buf.getvalue()

                            obj._data = cdata
                            obj[NameObject("/Width")]            = NumberObject(nw)
                            obj[NameObject("/Height")]           = NumberObject(nh)
                            obj[NameObject("/Filter")]           = NameObject("/DCTDecode")
                            obj[NameObject("/ColorSpace")]       = NameObject("/DeviceRGB" if img.mode == "RGB" else "/DeviceGray")
                            obj[NameObject("/BitsPerComponent")] = NumberObject(8)
                            obj[NameObject("/Length")]           = NumberObject(len(cdata))
                            if NameObject("/DecodeParms") in obj:
                                del obj[NameObject("/DecodeParms")]
                            images_processed += 1
                        except Exception:
                            images_failed += 1

            with open(output_path, "wb") as f:
                writer.write(f)

            orig = os.path.getsize(input_path)
            comp = os.path.getsize(output_path)
            pct  = (1 - comp / orig) * 100

            if images_processed == 0:
                return True, output_path, "No compressible images found (saved copy)."
            return True, output_path, f"Reduced by {pct:.1f}% ({images_processed} images)"
        except Exception as e:
            return False, None, str(e)

    # ── PDF → Images ZIP ──────────────────────────────────────────────────────

    @staticmethod
    def extract_images_to_zip(input_path, progress_callback=None):
        try:
            reader   = PdfReader(input_path)
            base_dir = App.get_running_app().user_data_dir
            tmp      = os.path.join(base_dir, "tmp_img_extract")
            if os.path.exists(tmp):
                shutil.rmtree(tmp)
            os.makedirs(tmp)

            count = 0
            MIN   = 300
            total = len(reader.pages)

            for pn, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback((pn + 1) / total * 90)
                res = page.get("/Resources")
                if not res:
                    continue
                xobj = res.get("/XObject")
                if not xobj:
                    continue
                if hasattr(xobj, "get_object"):
                    xobj = xobj.get_object()
                for name in xobj:
                    obj = xobj[name]
                    if hasattr(obj, "get_object"):
                        obj = obj.get_object()
                    if obj.get("/Subtype") != "/Image":
                        continue
                    try:
                        img = Image.open(io.BytesIO(obj.get_data()))
                        if img.width < MIN or img.height < MIN:
                            continue
                        count += 1
                        img.save(os.path.join(tmp, f"p{pn+1}_img{count}.png"))
                    except Exception as e:
                        logging.error(f"Image skip: {e}")

            if count == 0:
                return False, None, "No large images found in PDF."

            zip_path = os.path.join(base_dir, f"Images_{datetime.now().strftime('%H%M%S')}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fn in os.listdir(tmp):
                    zf.write(os.path.join(tmp, fn), fn)
            shutil.rmtree(tmp)
            if progress_callback:
                progress_callback(100)
            return True, zip_path, f"Extracted {count} images to ZIP."
        except Exception as e:
            return False, None, str(e)

    # ── Merge ─────────────────────────────────────────────────────────────────

    @staticmethod
    def merge_pdfs(files, progress_callback=None):
        try:
            writer = PdfWriter()
            for i, f in enumerate(files):
                for page in PdfReader(f).pages:
                    writer.add_page(page)
                if progress_callback:
                    progress_callback((i + 1) / len(files) * 100)
            out = PDFProcessor.get_save_path(files[0], "Merged")
            with open(out, "wb") as f:
                writer.write(f)
            return True, out, "Merged Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Split ─────────────────────────────────────────────────────────────────

    @staticmethod
    def split_pdf(file, pages, progress_callback=None):
        try:
            reader = PdfReader(file)
            writer = PdfWriter()
            parts  = pages.replace(" ", "").split(",")
            for i, p in enumerate(parts):
                if "-" in p:
                    s, e = map(int, p.split("-"))
                    for n in range(s - 1, e):
                        writer.add_page(reader.pages[n])
                else:
                    writer.add_page(reader.pages[int(p) - 1])
                if progress_callback:
                    progress_callback((i + 1) / len(parts) * 100)
            out = PDFProcessor.get_save_path(file, "Split")
            with open(out, "wb") as f:
                writer.write(f)
            return True, out, "Split Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Rotate ────────────────────────────────────────────────────────────────

    @staticmethod
    def rotate_pdf(file, angle, progress_callback=None):
        try:
            reader = PdfReader(file)
            writer = PdfWriter()
            total  = len(reader.pages)
            for i, page in enumerate(reader.pages):
                page.rotate(int(angle))
                writer.add_page(page)
                if progress_callback:
                    progress_callback((i + 1) / total * 100)
            out = PDFProcessor.get_save_path(file, f"Rotated_{angle}")
            with open(out, "wb") as f:
                writer.write(f)
            return True, out, "Rotated Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Watermark ─────────────────────────────────────────────────────────────

    @staticmethod
    def watermark_pdf(file, text, progress_callback=None):
        try:
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=A4)
            c.translate(297.5, 421)
            c.rotate(45)
            c.setFillColor(grey, alpha=0.5)
            c.setFont("Helvetica-Bold", 50)
            c.drawCentredString(0, 0, text)
            c.save()
            packet.seek(0)
            wm_page = PdfReader(packet).pages[0]

            reader = PdfReader(file)
            writer = PdfWriter()
            total  = len(reader.pages)
            for i, page in enumerate(reader.pages):
                page.merge_page(wm_page)
                writer.add_page(page)
                if progress_callback:
                    progress_callback((i + 1) / total * 100)
            out = PDFProcessor.get_save_path(file, "Watermarked")
            with open(out, "wb") as f:
                writer.write(f)
            return True, out, "Watermarked Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Encrypt ───────────────────────────────────────────────────────────────

    @staticmethod
    def encrypt_pdf(file, password, progress_callback=None):
        try:
            reader = PdfReader(file)
            writer = PdfWriter()
            total  = len(reader.pages)
            for i, page in enumerate(reader.pages):
                writer.add_page(page)
                if progress_callback:
                    progress_callback((i + 1) / total * 100)
            writer.encrypt(password)
            out = PDFProcessor.get_save_path(file, "Protected")
            with open(out, "wb") as f:
                writer.write(f)
            return True, out, "Encrypted Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Extract Text ──────────────────────────────────────────────────────────

    @staticmethod
    def extract_text(file, progress_callback=None):
        try:
            reader = PdfReader(file)
            total  = len(reader.pages)
            lines  = []
            for i, page in enumerate(reader.pages):
                lines.append(page.extract_text() or "")
                if progress_callback:
                    progress_callback((i + 1) / total * 100)
            out = PDFProcessor.get_save_path(file, "Extracted", ".txt")
            with open(out, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True, out, "Extracted Successfully"
        except Exception as e:
            return False, None, str(e)

    # ── Extract Text+ ─────────────────────────────────────────────────────────

    @staticmethod
    def extract_text_enhanced(file, progress_callback=None):
        """Enhanced extraction: per-page stats, word count, summary."""
        try:
            reader      = PdfReader(file)
            total       = len(reader.pages)
            lines       = []
            total_words = 0
            total_chars = 0

            lines.append("=" * 60)
            lines.append("  EXTRACTED TEXT REPORT")
            lines.append(f"  File   : {os.path.basename(file)}")
            lines.append(f"  Pages  : {total}")
            lines.append(f"  Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("=" * 60)

            for i, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback(10 + (i + 1) / total * 80)
                text        = page.extract_text() or ""
                words       = len(text.split())
                chars       = len(text)
                total_words += words
                total_chars += chars

                lines.append(f"\n{'─' * 60}")
                lines.append(f"  PAGE {i+1}  |  {words} words  |  {chars} characters")
                lines.append(f"{'─' * 60}")
                if text.strip():
                    for para in text.split("\n\n"):
                        c = para.strip()
                        if c:
                            lines.append(c)
                            lines.append("")
                else:
                    lines.append("[No extractable text on this page]")

            lines.append("\n" + "=" * 60)
            lines.append("  SUMMARY")
            lines.append(f"  Total pages : {total}")
            lines.append(f"  Total words : {total_words:,}")
            lines.append(f"  Total chars : {total_chars:,}")
            lines.append(f"  Avg words/page: {total_words // max(total, 1):,}")
            lines.append("=" * 60)

            out = PDFProcessor.get_save_path(file, "ExtractedPlus", ".txt")
            with open(out, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            if progress_callback:
                progress_callback(100)
            return True, out, f"Extracted {total_words:,} words from {total} pages"
        except Exception as e:
            return False, None, str(e)

    # ── Page Numbers ──────────────────────────────────────────────────────────

    @staticmethod
    def add_page_numbers(file, position="bottom-center", start_num=1,
                         font_size=12, prefix="", suffix="",
                         progress_callback=None):
        try:
            reader = PdfReader(file)
            writer = PdfWriter()
            total  = len(reader.pages)

            for idx, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback((idx + 1) / total * 90)
                pb = page.mediabox
                pw, ph = float(pb.width), float(pb.height)
                num_text = f"{prefix}{idx + start_num}{suffix}"
                margin   = 24

                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=(pw, ph))
                c.setFont("Helvetica", font_size)
                c.setFillColorRGB(0.2, 0.2, 0.2)
                if   position == "bottom-center": c.drawCentredString(pw/2, margin, num_text)
                elif position == "bottom-left":   c.drawString(margin, margin, num_text)
                elif position == "bottom-right":  c.drawRightString(pw-margin, margin, num_text)
                elif position == "top-center":    c.drawCentredString(pw/2, ph-margin-font_size, num_text)
                elif position == "top-left":      c.drawString(margin, ph-margin-font_size, num_text)
                elif position == "top-right":     c.drawRightString(pw-margin, ph-margin-font_size, num_text)
                c.save()
                packet.seek(0)
                page.merge_page(PdfReader(packet).pages[0])
                writer.add_page(page)

            out = PDFProcessor.get_save_path(file, "PageNumbered")
            with open(out, "wb") as f:
                writer.write(f)
            if progress_callback:
                progress_callback(100)
            return True, out, f"Page numbers added ({total} pages)"
        except Exception as e:
            return False, None, str(e)

    # ── Header / Footer ───────────────────────────────────────────────────────

    @staticmethod
    def add_header_footer(file, header_text="", footer_text="",
                          font_size=11, progress_callback=None):
        try:
            if not header_text and not footer_text:
                return False, None, "Please enter header or footer text."
            reader = PdfReader(file)
            writer = PdfWriter()
            total  = len(reader.pages)

            for idx, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback((idx + 1) / total * 90)
                pb = page.mediabox
                pw, ph = float(pb.width), float(pb.height)
                margin = 20

                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=(pw, ph))
                c.setFont("Helvetica", font_size)
                c.setFillColorRGB(0.15, 0.15, 0.15)

                if header_text:
                    ht = header_text.replace("{page}", str(idx+1)).replace("{total}", str(total))
                    c.drawCentredString(pw/2, ph-margin-font_size, ht)
                    c.setStrokeColorRGB(0.7, 0.7, 0.7)
                    c.setLineWidth(0.5)
                    c.line(margin, ph-margin-font_size-4, pw-margin, ph-margin-font_size-4)

                if footer_text:
                    ft = footer_text.replace("{page}", str(idx+1)).replace("{total}", str(total))
                    c.setStrokeColorRGB(0.7, 0.7, 0.7)
                    c.setLineWidth(0.5)
                    c.line(margin, margin+font_size+6, pw-margin, margin+font_size+6)
                    c.drawCentredString(pw/2, margin, ft)

                c.save()
                packet.seek(0)
                page.merge_page(PdfReader(packet).pages[0])
                writer.add_page(page)

            out = PDFProcessor.get_save_path(file, "HeaderFooter")
            with open(out, "wb") as f:
                writer.write(f)
            if progress_callback:
                progress_callback(100)
            parts = (["header"] if header_text else []) + (["footer"] if footer_text else [])
            return True, out, f"Added {' & '.join(parts)} to {total} pages"
        except Exception as e:
            return False, None, str(e)

    # ── Repair ────────────────────────────────────────────────────────────────

    @staticmethod
    def repair_pdf(file, progress_callback=None):
        try:
            if progress_callback: progress_callback(10)
            reader = PdfReader(file, strict=False)
            if progress_callback: progress_callback(30)
            writer    = PdfWriter()
            total     = len(reader.pages)
            recovered = 0
            errors    = []
            for i, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback(30 + (i+1)/total * 55)
                try:
                    writer.add_page(page)
                    recovered += 1
                except Exception as e:
                    errors.append(f"Page {i+1}: {e}")
            try:
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
            except Exception:
                pass
            out = PDFProcessor.get_save_path(file, "Repaired")
            with open(out, "wb") as f:
                writer.write(f)
            if progress_callback: progress_callback(100)
            msg = f"Recovered {recovered}/{total} pages."
            if errors:
                msg += f" {len(errors)} page(s) had issues."
            return True, out, msg
        except Exception as e:
            return False, None, f"Could not open file: {e}"

    # ── Redact ────────────────────────────────────────────────────────────────

    @staticmethod
    def redact_text(file, keywords, progress_callback=None):
        try:
            if not keywords:
                return False, None, "No keywords provided."
            reader        = PdfReader(file)
            writer        = PdfWriter()
            total         = len(reader.pages)
            redacted_count = 0

            for idx, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback((idx+1)/total * 85)
                pb = page.mediabox
                pw, ph = float(pb.width), float(pb.height)
                text = page.extract_text() or ""

                found = False
                for kw in keywords:
                    if kw.lower() in text.lower():
                        found = True
                        redacted_count += text.lower().count(kw.lower())

                if found:
                    text_lines = text.split("\n")
                    lcount     = len(text_lines)
                    usable_h   = ph - 80
                    line_h     = usable_h / max(lcount, 1)
                    start_y    = ph - 40

                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=(pw, ph))
                    c.setFillColorRGB(0, 0, 0)
                    for li, line in enumerate(text_lines):
                        ll = line.lower()
                        for kw in keywords:
                            if kw.lower() in ll:
                                y       = start_y - li * line_h
                                ks      = ll.find(kw.lower())
                                char_w  = pw / max(len(line), 1)
                                x       = 36 + ks * char_w
                                box_w   = len(kw) * char_w * 1.2
                                c.rect(max(0, x-2), y-2, min(box_w+4, pw-x), line_h*0.85, fill=1, stroke=0)
                    c.save()
                    packet.seek(0)
                    page.merge_page(PdfReader(packet).pages[0])

                writer.add_page(page)

            out = PDFProcessor.get_save_path(file, "Redacted")
            with open(out, "wb") as f:
                writer.write(f)
            if progress_callback: progress_callback(100)
            kw_list = ", ".join(f'"{k}"' for k in keywords)
            return True, out, f"Redacted ~{redacted_count} occurrence(s) of: {kw_list}"
        except Exception as e:
            return False, None, str(e)
