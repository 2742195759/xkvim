from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput
from .func_register import vim_register
from .vim_utils import SetVimRegister

class TranslatorBuffer(WidgetBufferWithInputs): 
    def __init__(self):
        widgets = [
            SimpleInput(prom="input", name="input"),
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

@vim_register(command="Fanyi")
def TestBaidufanyi(args):
    ff = TranslatorBuffer()
    ff.create()
    ff.show()
    
