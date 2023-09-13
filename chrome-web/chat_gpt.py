import asyncio
from pyppeteer import launch
import pyppeteer
import os
import time
from pyppeteer_stealth import stealth
import sys
import copy

#ghp_7zs8prCylBa02mLyBnWliVlkTQRcFe2t0TpF

# NOTE: update the chromium version to `1194470`
pyppeteer.launcher.DEFAULT_ARGS.remove("--enable-automation")

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--query",                  type=str,   default="你好",  help="data path")
    parser.add_argument("--prompt",                 type=str,   default="no",  help="data path")
    parser.add_argument("--cookie",                 type=str,   help="data path")
    parser.add_argument("--proxy",                  type=str,   default=""  ,  help="data path")
    parser.add_argument("--login",                  type=str,   default="no"  ,  help="data path")
    return parser.parse_args()

# NOTE: change this when web version update.
text_area_class = "prompt-textarea"
cmd_args = parameter_parser()
def do_every(total, every):
    for i in range(int(total / every)): 
        time.sleep(every)
        yield i

async def wait_output(page):
    tot_time = 120
    loop_time = 0.3
    for i in range(int(tot_time / loop_time)):
        time.sleep(loop_time)
        element = await page.querySelector("button[data-testid='send-button']")
        element = await element.querySelector("span[data-state='closed']")
        if element != "none" and element is not None: 
            return True
    return False

async def login(): # Google 账号的登录依赖 headless=False，否则无法登录。所以无法在服务器端使用，但是可以在mac上使用。
    browser = await launch(userDataDir=r"./ChromeCache", headless=False, options={'args': ['--no-sandbox', '--proxy-server=http://agent.baidu.com:8891'], 'defaultViewport': {'width': 1920, 'height': 1080}})
    page = await browser.newPage()
    await page.goto('https://chat.openai.com')
    time.sleep(5.0)
    buttons = await page.JJ("button.btn-primary")
    for button in buttons:
        text = await page.evaluate('(element) => element.textContent', button)
        if text == "Okay, let’s go":
            await page.evaluate('(element) => element.click()', button)
    time.sleep(1.0)
    breakpoint() 
    
async def process_loop(promote=True):
    browser = await launch(userDataDir=r"./ChromeCache", headless=True, options={'args': ['--no-sandbox', '--proxy-server=http://agent.baidu.com:8891'], 'defaultViewport': {'width': 1920, 'height': 1080}})
    page = await browser.newPage()
    await page.evaluate("Object.defineProperties(navigator,{ webdriver:{ get: () => false } })", force_expr=True)
    await page.setBypassCSP(True)
    await stealth(page)  # <-- Here

    #await page.evaluate("""
        #Object.defineProperty(window.document,'hidden',{get:function(){return false;},configurable:true});
        #Object.defineProperty(window.document,'visibilityState',{get:function(){return 'visible';},configurable:true});
        #window.document.dispatchEvent(new Event('visibilitychange'));""", force_expr=True);

    # change the page visiblity...
    await page.evaluateOnNewDocument("""
        Object.defineProperty(window.document,'hidden',{get:function(){return false;},configurable:true});
        Object.defineProperty(window.document,'visibilityState',{get:function(){return 'visible';},configurable:true});
    """);

    await page.goto('https://chat.openai.com')
    #print ("HideState: ", await page.evaluate('document.visibilityState', force_expr=True))
    time.sleep(5.0)
    buttons = await page.JJ("button.btn-primary")
    for button in buttons:
        text = await page.evaluate('(element) => element.textContent', button)
        if text == "Okay, let’s go":
            await page.evaluate('(element) => element.click()', button)
    time.sleep(1.0)
    pages = await browser.pages()
    # input the text and query yiyan.
    while True:
        if promote: 
            await page.screenshot({'path': 'example.png'})
            print ("请输入你的文本：(\\n\\n结束输入)")
        try:
            inputs = []
            while True:
                inp = input()
                if inp.strip() == "": break
                inputs.append(inp)
        except:
            # EOF, Exit this subprocess.
            break
        if promote:
            print ("处理中...")
        if inp == "quit": 
            break

        for inp in inputs:
            await page.type(f"textarea#{text_area_class}", inp, delay=1)
            # simulate a \n in chatgpt textarea.
            await page.keyboard.down("Shift")
            await page.keyboard.press("Enter")
            await page.keyboard.up("Shift")

        time.sleep(2.0)
        await page.click(f"button[data-testid='send-button']")
        time.sleep(1.0)
        if await wait_output(page) == False: 
            print ("TimeOut")
        else:
            await page.screenshot({'path': 'example.png'})
            # Extract the output from the page
            responses = await page.JJ("div.markdown")
            #for response in responses:
            outputs = []
            for response in responses[::-1]: 
                output = await page.evaluate('(element) => element.innerHTML', response)
                outputs.append(render(output))
            to_output = [ line.strip("\n") for line in outputs[0].split("\n") if line.strip() != "" ]
            print("\n".join(to_output))
        print("") # empty line for seperating.
        sys.stdout.flush()
    await browser.close()

from html.parser import HTMLParser
from html.entities import name2codepoint

class Node:
    def __init__(self, tag, attr, father=None):
        self.childs = []
        self.father = father
        if father is not None:
            father.append_child(self)
        self.tag = tag
        self.attr = attr

    def append_child(self, child):
        self.childs.append(child)
        child.father = self

    def append_data(self, data):
        self.childs.append(data)

    def render_to_text(self):
        return Render(self).render(self)

    def has_class(self, class_name):
        if "class" in self.attr and class_name in self.attr["class"]: return True        
        return False

class Data: 
    def __init__(self, string):
        self.text = string

class Render:
    def __init__(self, root):
        self.root = root

    def render(self, root):
        outputs = []
        for child in root.childs:
            if isinstance(child, Data): outputs.append(child.text)
            if isinstance(child, Node): outputs.append(self.render(child))
        tag = root.tag
        res = getattr(self, f"render_{tag}", self.render_default)(root, outputs)
        assert isinstance(res, str)
        return res

    def render_p(self, node, child_str_outs): 
        return "".join(child_str_outs) + "\n"

    def render_default(self, node, child_str_outs):
        return "".join(child_str_outs)

    def render_div(self, node, child_str_outs):
        if node.has_class("font-sans") and node.has_class("rounded-t-md"): 
            # code head block
            lang = node.childs[0].childs[0].text + "\n"
            return lang
        return self.render_default(node, child_str_outs)

    def render_pre(self, node, child_str_outs):
        # code
        return "```" + self.render_default(node, child_str_outs) + "```\n"

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # lists of fields to be extracted
        self.stack = []
        self.root = Node("root", None, None)
        self.stack.append(self.root)
        
    def wrapper(self, tag, attrs, tmp_out):
        if 'class' in attrs and attrs['class'] in ['code-copy-text', 'code-lang']: 
            return []
        if tag == "tr": tmp_out.append("\n")
        if tag == "p": tmp_out.append("\n")
        if tag == "pre": 
            if 'class' in attrs and 'bg-black' in attrs['class']:
                breakpoint() 
                family = attrs['class'].replace("language-", "")
                tmp_out[0:0] = f"```{family}\n"
                tmp_out.append("\n```")
            else: 
                tmp_out[0:0] = "```"
                tmp_out.append("```")
        return tmp_out

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append(Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        self.stack.pop(-1)

    def handle_data(self, data):
        self.stack[-1].append_data(Data(data))

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        self.stack[-1].append_data(Data(c))

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        self.stack[-1].append_data(Data(c))

    def get_output(self):
        return self.root.render_to_text()

def render(innerhtml_content):
    """ render html content and return a ascii text. """
    with open("./render.log", "w") as fp :
        fp.write(innerhtml_content)
    parser = MyHTMLParser()
    parser.feed(innerhtml_content)
    return parser.get_output()

def test():
    print("".join(render("<p>hello</p>")))
    with open("../html.txt", "r") as fp :
        lines = fp.readlines()
    breakpoint() 
    print("".join(render("".join(lines))))

#test()

if cmd_args.login == "yes": 
    asyncio.get_event_loop().run_until_complete(login())
else: 
    asyncio.get_event_loop().run_until_complete(process_loop(cmd_args.prompt == "yes"))
