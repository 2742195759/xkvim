from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI
import vim

class BrowserSearchBuffer(WidgetBufferWithInputs): 
    def __init__(self, name, title, hint=None):
        if not hint:
            hint = "输入enter键，在mac上打开网页:"
        widgets = [
            SimpleInput(prom="input", name="input"),
            TextWidget(hint, name=""),
        ]
        options = {
            'title': title, 
            'maxwidth': 100, 
            'minwidth': 50,
            'maxheight': 3, 
        }
        root = WidgetList("", widgets, reverse=False)
        super().__init__(root, name, None, options)

    def on_insert_input(self, key):
        if key == '<cr>': 
            text = self.widgets["input"].text
            self.on_enter(text)
            self.close()
            return True
        self.widgets["input"].on_type(key)
        self.redraw()
        return True

    def on_enter(self, text):
        raise NotImplementedError("Please implement the on_enter method")

class GoogleSearch(BrowserSearchBuffer): 
    def __init__(self):
        super().__init__("Google", "Google搜索")

    def on_enter(self, text):
        vim.command(f"Google {text}")

class PaddleDocSearch(BrowserSearchBuffer): 
    def __init__(self):
        super().__init__("PaddleDoc", "Paddle文档搜索")

    def on_enter(self, text):
        vim.command(f"Pdoc {text}")

class TranslatorBuffer(WidgetBufferWithInputs): 
    def __init__(self):
        widgets = [
            SimpleInput(prom="input", name="input"),
            TextWidget("翻译:", name=""),
            TextWidget("", name="show"),
        ]
        options = {
            'title': "百度翻译", 
            'maxwidth': 100, 
            'minwidth': 50,
            'maxheight': 3, 
        }
        root = WidgetList("", widgets, reverse=False)
        super().__init__(root, "BaiduFanyi", None, options)

    def on_insert_input(self, key):
        if key == '<cr>': 
            return self.on_translate()
        self.widgets["input"].on_type(key)
        self.redraw()
        return True

    def on_translate(self): 
        from .converse_plugin import baidu_translate
        result = baidu_translate(self.widgets["input"].text)
        self.widgets["show"].text = result
        self.redraw()

    def on_exit(self):
        translated = self.widgets["show"].text
        SetVimRegister('"', translated)
        if vim.eval("mode()") == 'i': 
            # insert mode, we just insert the translated text
            vim.command(f'execute "normal i{translated}"')
            Normal_GI()

@vim_register(command="Fanyi")
def TestBaidufanyi(args):
    ff = TranslatorBuffer()
    ff.create()
    ff.show()
    
@vim_register(command="GoogleUI")
def TestGoogleUI(args):
    ff = GoogleSearch()
    ff.create()
    ff.show()

@vim_register(command="PdocUI")
def TestPdocUI(args):
    ff = PaddleDocSearch()
    ff.create()
    ff.show()
    
    
