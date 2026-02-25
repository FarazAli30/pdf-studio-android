"""
kv_layout.py
------------
All Kivy KV markup for PDF Studio.
"""

KV = """
#:import dp kivy.metrics.dp
#:import os os

<MaterialButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: (0, 0, 0, 0)
    color: (1, 1, 1, 1)
    font_size: '16sp'
    bold: True
    size_hint_y: None
    height: dp(56)
    canvas.before:
        Color:
            rgba: (0.2, 0.45, 0.9, 1) if self.state == 'normal' and not self.disabled else (0.15, 0.35, 0.7, 1) if not self.disabled else (0.6, 0.6, 0.6, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(28),]

<SecondaryButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: (0, 0, 0, 0)
    color: (0, 0.1, 0.2, 1)
    font_size: '15sp'
    size_hint_y: None
    height: dp(48)
    canvas.before:
        Color:
            rgba: (0.85, 0.9, 1, 1) if self.state == 'normal' else (0.75, 0.85, 0.95, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(24),]

<MenuCard@ButtonBehavior+BoxLayout>:
    orientation: 'vertical'
    padding: dp(20)
    spacing: dp(10)
    size_hint_y: None
    height: dp(140)
    canvas.before:
        Color:
            rgba: (0.88, 0.9, 0.94, 1) if self.state == 'normal' else (0.8, 0.85, 0.9, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(24),]
    icon: ""
    title: ""
    desc: ""
    Label:
        text: root.icon
        font_name: 'EmojiFont'
        font_size: '32sp'
        color: (0.2, 0.45, 0.9, 1)
        size_hint_y: None
        height: dp(40)
    Label:
        text: root.title
        font_size: '18sp'
        bold: True
        color: (0.1, 0.12, 0.14, 1)
        halign: 'center'
        valign: 'middle'
        text_size: self.width, None
    Label:
        text: root.desc
        font_size: '12sp'
        color: (0.4, 0.45, 0.5, 1)
        halign: 'center'
        valign: 'top'
        text_size: self.width, None

<InfoPopup>:
    title: ""
    separator_height: 0
    background: ""
    background_color: (0,0,0,0)
    size_hint: .85, None
    height: dp(200)
    BoxLayout:
        orientation: 'vertical'
        padding: dp(24)
        spacing: dp(20)
        canvas.before:
            Color:
                rgba: (0.95, 0.96, 0.98, 1)
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(28),]
        Label:
            text: root.message
            color: (0.1, 0.12, 0.14, 1)
            halign: 'center'
            font_size: '16sp'
            text_size: self.width, None
        MaterialButton:
            text: "OK"
            height: dp(48)
            on_release: root.dismiss()

<FilePopup>:
    title: "Select Files"
    title_color: (0.1, 0.12, 0.14, 1)
    background_color: (0.95, 0.96, 0.98, 1)
    size_hint: .95, .95
    BoxLayout:
        orientation: 'vertical'
        padding: dp(16)
        spacing: dp(16)
        FileChooserListView:
            id: filechooser
            path: '.'
            filters: root.filters
            multiselect: root.multiselect
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12),]
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            spacing: dp(12)
            SecondaryButton:
                text: "CANCEL"
                on_release: root.dismiss()
            MaterialButton:
                text: "SELECT"
                on_release: root.load(filechooser.selection)

<BaseToolScreen>:
    canvas.before:
        Color:
            rgba: (0.95, 0.96, 0.98, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: [dp(8), 0]
            Button:
                text: "🔙"
                font_name: 'EmojiFont'
                font_size: '24sp'
                size_hint_x: None
                width: dp(48)
                background_color: (0,0,0,0)
                color: (0.1, 0.12, 0.14, 1)
                on_release: app.root.current = 'menu'
            Label:
                text: root.tool_title
                font_size: '22sp'
                color: (0.1, 0.12, 0.14, 1)
                bold: True
                halign: 'left'
                text_size: self.width, None
            Button:
                text: "Clear Session" if root.working_file else ""
                opacity: 1 if root.working_file else 0
                disabled: not root.working_file
                size_hint_x: None
                width: dp(100)
                color: (0.8, 0.2, 0.2, 1)
                background_color: (0,0,0,0)
                on_release: root.clear_session()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                padding: dp(20)
                spacing: dp(24)
                size_hint_y: None
                height: self.minimum_height
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(16)
                    spacing: dp(8)
                    canvas.before:
                        Color:
                            rgba: (0.85, 0.9, 1, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(20),]
                    Label:
                        text: "Instruction"
                        bold: True
                        color: (0.2, 0.45, 0.9, 1)
                        size_hint_y: None
                        height: dp(24)
                        halign: 'left'
                        text_size: self.width, None
                    Label:
                        text: root.tool_info
                        font_size: '14sp'
                        color: (0.1, 0.12, 0.14, 1)
                        size_hint_y: None
                        height: self.texture_size[1]
                        halign: 'left'
                        text_size: self.width, None
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(12)
                    size_hint_y: None
                    height: self.minimum_height
                    Label:
                        text: "FILE SELECTION"
                        font_size: '12sp'
                        bold: True
                        color: (0.4, 0.45, 0.5, 1)
                        size_hint_y: None
                        height: dp(20)
                    BoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(10)
                        Label:
                            text: root.status_message
                            font_size: '13sp'
                            color: (0.2, 0.45, 0.9, 1)
                            size_hint_y: None
                            height: dp(30) if root.status_message else 0
                            opacity: 1 if root.status_message else 0
                        BoxLayout:
                            size_hint_y: None
                            height: dp(48)
                            spacing: dp(10)
                            SecondaryButton:
                                text: "Add PDF" if (root.name == 'merge' and root.working_file) else ("Change File" if root.working_file else "Choose Files")
                                on_release: root.open_file_browser()
                            Button:
                                text: "Preview"
                                size_hint_x: 0.38 if root.working_file else 0.001
                                opacity: 1 if root.working_file else 0
                                disabled: not root.working_file
                                background_color: (0,0,0,0)
                                color: (0.2, 0.45, 0.9, 1)
                                bold: True
                                font_size: '14sp'
                                on_release: root.preview_file()
                            Button:
                                text: "Clear List"
                                size_hint_x: 0.4 if (root.name == 'merge' and root.selected_files) else 0.001
                                opacity: 1 if (root.name == 'merge' and root.selected_files) else 0
                                disabled: not (root.name == 'merge' and root.selected_files)
                                background_color: (0,0,0,0)
                                color: (0.8, 0.2, 0.2, 1)
                                on_release: root.reset_merge_list()
                BoxLayout:
                    id: input_area
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(16)
                Widget:
                    size_hint_y: None
                    height: dp(20)
                BoxLayout:
                    size_hint_y: None
                    height: dp(30) if root.is_processing else 0
                    opacity: 1 if root.is_processing else 0
                    spacing: dp(10)
                    ProgressBar:
                        id: progress_bar
                        max: 100
                        value: root.progress_value
                    Label:
                        text: str(int(root.progress_value)) + "%"
                        size_hint_x: None
                        width: dp(40)
                        color: (0.2, 0.45, 0.9, 1)
                        bold: True
                        font_size: '14sp'
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(10)
                    MaterialButton:
                        id: process_btn
                        text: "PROCESS" if not root.is_processing else "..."
                        disabled: root.is_processing
                        on_release: root.process_action()
                    MaterialButton:
                        id: preview_btn
                        text: "PREVIEW"
                        size_hint_y: None
                        height: dp(56) if root.download_ready else 0
                        opacity: 1 if root.download_ready else 0
                        disabled: not root.download_ready or root.is_processing
                        on_release: root.preview_file()
                        canvas.before:
                            Color:
                                rgba: (0.2, 0.45, 0.9, 1) if self.state == 'normal' else (0.15, 0.35, 0.75, 1)
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(28),]
                    MaterialButton:
                        id: download_btn
                        text: "DOWNLOAD ZIP" if root.name == 'pdf2img' else "DOWNLOAD"
                        size_hint_y: None
                        height: dp(56) if root.download_ready else 0
                        opacity: 1 if root.download_ready else 0
                        disabled: not root.download_ready or root.is_processing
                        on_release: root.download_result()
                        canvas.before:
                            Color:
                                rgba: (0.1, 0.7, 0.3, 1) if self.state == 'normal' else (0.05, 0.5, 0.2, 1)
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(28),]

<MenuScreen>:
    BoxLayout:
        orientation: 'vertical'

        # Header
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(120)
            padding: [dp(24), dp(40), dp(24), dp(10)]
            Label:
                text: "PDF Studio"
                font_size: '36sp'
                bold: True
                color: (0.1, 0.12, 0.14, 1)
                halign: 'left'
                text_size: self.width, None
            Label:
                text: "Professional Document Suite"
                font_size: '16sp'
                color: (0.4, 0.45, 0.5, 1)
                halign: 'left'
                text_size: self.width, None

        # Session bar
        BoxLayout:
            size_hint_y: None
            height: dp(60) if app.session_file else 0
            opacity: 1 if app.session_file else 0
            padding: [dp(24), dp(5)]
            canvas.before:
                Color:
                    rgba: (0.85, 0.9, 1, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(15),]
            Label:
                text: "Editing: " + (os.path.basename(app.session_file) if app.session_file else "")
                color: (0.2, 0.45, 0.9, 1)
                bold: True
                text_size: self.width, None
                halign: 'left'
                valign: 'middle'
            Button:
                text: "Clear File"
                size_hint_x: None
                width: dp(80)
                background_color: (0,0,0,0)
                color: (0.8, 0.2, 0.2, 1)
                on_release: app.clear_session()
            Button:
                text: "Save File"
                size_hint_x: None
                width: dp(80)
                background_color: (0,0,0,0)
                color: (0.1, 0.6, 0.2, 1)
                on_release: app.save_session_file()

        # Tool grid
        ScrollView:
            do_scroll_x: False
            GridLayout:
                padding: [dp(24), dp(16), dp(24), dp(8)]
                cols: 2
                spacing: dp(16)
                size_hint_y: None
                height: self.minimum_height
                MenuCard:
                    icon: "📉"
                    font_name: 'EmojiFont'
                    title: "Compress"
                    desc: "Reduce file size"
                    on_release: app.root.current = 'compress'
                MenuCard:
                    icon: "🖼️"
                    font_name: 'EmojiFont'
                    title: "PDF to Images"
                    desc: "Extract all images"
                    on_release: app.root.current = 'pdf2img'
                MenuCard:
                    icon: "📄"
                    font_name: 'EmojiFont'
                    title: "Images to PDF"
                    desc: "Convert photos to PDF"
                    on_release: app.root.current = 'img2pdf'
                MenuCard:
                    icon: "🔗"
                    title: "Merge"
                    desc: "Combine multiple PDFs"
                    on_release: app.root.current = 'merge'
                MenuCard:
                    icon: "✂️"
                    title: "Split"
                    desc: "Extract specific pages"
                    on_release: app.root.current = 'split'
                MenuCard:
                    icon: "🔄"
                    title: "Rotate"
                    desc: "Change page orientation"
                    on_release: app.root.current = 'rotate'
                MenuCard:
                    icon: "🏷️"
                    title: "Watermark"
                    desc: "Add security overlay"
                    on_release: app.root.current = 'watermark'
                MenuCard:
                    icon: "🔒"
                    title: "Protect"
                    desc: "Encrypt with password"
                    on_release: app.root.current = 'encrypt'
                MenuCard:
                    icon: "ℹ️"
                    title: "Metadata"
                    desc: "View file properties"
                    on_release: app.root.current = 'info'
                MenuCard:
                    icon: "🔢"
                    font_name: 'EmojiFont'
                    title: "Page Numbers"
                    desc: "Stamp page numbers"
                    on_release: app.root.current = 'pagenum'
                MenuCard:
                    icon: "📑"
                    font_name: 'EmojiFont'
                    title: "Header/Footer"
                    desc: "Add header or footer text"
                    on_release: app.root.current = 'headerfooter'
                MenuCard:
                    icon: "📃"
                    font_name: 'EmojiFont'
                    title: "Extract Text+"
                    desc: "Enhanced text extraction"
                    on_release: app.root.current = 'extract_plus'
                MenuCard:
                    icon: "🔧"
                    font_name: 'EmojiFont'
                    title: "Repair PDF"
                    desc: "Fix corrupted PDFs"
                    on_release: app.root.current = 'repair'
                MenuCard:
                    icon: "⬛"
                    font_name: 'EmojiFont'
                    title: "Redact Text"
                    desc: "Black out sensitive text"
                    on_release: app.root.current = 'redact'

        # GitHub / Source Code footer button
        BoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: [dp(20), dp(8)]
            canvas.before:
                Color:
                    rgba: (0.93, 0.94, 0.97, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                background_normal: ''
                background_down: ''
                background_color: (0, 0, 0, 0)
                on_release: app.open_github()
                canvas.before:
                    Color:
                        rgba: (0.10, 0.10, 0.10, 1) if self.state == 'normal' else (0.05, 0.05, 0.05, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(22),]
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    padding: [dp(20), 0]
                    pos: self.parent.pos
                    size: self.parent.size
                    Label:
                        text: "[b]</>[/b]"
                        markup: True
                        font_size: '18sp'
                        size_hint_x: None
                        width: dp(32)
                        color: (1, 1, 1, 1)
                    Label:
                        text: "[b]Source Code[/b]  —  View on GitHub"
                        markup: True
                        font_size: '14sp'
                        color: (0.85, 0.88, 1, 1)
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.width, None
"""
