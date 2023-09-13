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
    parser.add_argument("--debug",                  type=str,   default="no"  ,  help="data path")
    return parser.parse_args()

# NOTE: change this when web version update.
text_area_class = "prompt-textarea"
send_area_class = "VAtmtpqL"

cmd_args = parameter_parser()
if cmd_args.debug == "yes": 
    """
    Step1: 
        Visit http://10.255.125.22:8086/json/list to get frontendURI
    Step2: 
        Visit http://10.255.125.22:8086/{DevToolFrontendURL} to access the remote debugging. 

    Useful for login and record cookies.

    If you want to use http_proxy.py and you want to access it from outside: 
    Step1: 
        change: search `server` and change it to `127.0.0.1:10000` if your chrome listen in 0.0.0.0:10000
    Step2: 
        add listen port and expose it by docker.
    """
    from pyppeteer.launcher import Launcher
    pyppeteer.launcher.DEFAULT_ARGS.append("--remote-debugging-address=0.0.0.0")
    pyppeteer.launcher.DEFAULT_ARGS.append("--remote-debugging-port=10000")
    print(' '.join(Launcher(userDataDir=f"{cmd_args.cookie}", headless=True, options={'args': ['--no-sandbox'], 'defaultViewport': {'width': 1920, 'height': 1080}}).cmd))

def do_every(total, every):
    for i in range(int(total / every)): 
        time.sleep(every)
        yield i

async def wait_output(page):
    tot_time = 120
    loop_time = 0.3
    for i in range(int(tot_time / loop_time)):
        time.sleep(loop_time)
        await page.focus(f"button[data-testid='send-button']")
        element = await page.querySelector("button[data-testid='send-button']")
        element = await element.querySelector("span[data-state='closed']")
        if element != "none": 
            return True
    return False

async def login(): # Google 账号的登录依赖 headless=False，否则无法登录。所以无法在服务器端使用，但是可以在mac上使用。
    browser = await launch(userDataDir=r"C:\Users\xiongkun\Desktop\linux", headless=False, options={'args': ['--no-sandbox'], 'defaultViewport': {'width': 1920, 'height': 1080}})
    page = await browser.newPage()
    await page.goto('https://chat.openai.com')
    
async def process_loop(promote=True):
    browser = await launch(userDataDir=r"C:\Users\xiongkun\Desktop\linux", headless=True, options={'args': ['--no-sandbox'], 'defaultViewport': {'width': 1920, 'height': 1080}})
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
    print ("HideState: ", await page.evaluate('document.visibilityState', force_expr=True))
    time.sleep(10.0)
    pages = await browser.pages()
    # input the text and query yiyan.
    while True:
        if promote: 
            print ("请输入你的文本：")
        try:
            inp = input()
        except:
            # EOF, Exit this subprocess.
            break
        if inp == "quit": 
            break

        await page.type(f"textarea#{text_area_class}", inp, delay=5)
        time.sleep(3.0)
        await page.click(f"button[data-testid='send-button']")
        await page.click(f"button[data-testid='send-button']")
        time.sleep(3.0)

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
                #outputs.append(output)
                outputs.append(render(output))
            to_output = [ line.strip("\n") for line in outputs[0].split("\n") if line.strip() != "" ]
            print("\n".join(to_output))
        print("") # empty line for seperating.
        sys.stdout.flush()
    await browser.close()

from html.parser import HTMLParser
from html.entities import name2codepoint

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # lists of fields to be extracted
        self.stack = []
        
    def wrapper(self, tag, attrs, tmp_out):
        if 'class' in attrs and attrs['class'] in ['code-copy-text', 'code-lang']: 
            return []
        if tag == "tr": tmp_out.append("\n")
        if tag == "p": tmp_out.append("\n")
        if tag == "code": 
            if 'class' in attrs and 'language' in attrs['class']:
                family = attrs['class'].replace("language-", "")
                tmp_out[0:0] = f"```{family}\n"
                tmp_out.append("\n```")
            else: 
                tmp_out[0:0] = "```"
                tmp_out.append("```")
        return tmp_out

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs))

    def extend_list(self, items):
        extended = []
        for out in items: 
            extended.extend(out)
        return extended

    def handle_endtag(self, tag):
        tmp_out = []
        finded = False
        while len(self.stack) > 0: 
            if isinstance(self.stack[-1], tuple) and self.stack[-1][0] == tag:
                tag, attrs = self.stack.pop()
                tmp_out = list(reversed(tmp_out))
                tmp_out = self.extend_list(tmp_out)
                tmp_out = self.wrapper(tag, attrs, tmp_out)
                self.stack.append(tmp_out)
                finded = True
                break
            else:
                out = self.stack.pop()
                if not isinstance(out, tuple):
                    """ <input> may not close. just ignore it.
                    """
                    tmp_out.append(out)
        if finded is False:
            raise Exception(f"Error: tag not closed. {tag}")

    def handle_data(self, data):
        self.stack.append(data)

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        self.stack.append(c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        self.stack.append(c)

    def get_output(self):
        output = self.extend_list(self.stack)
        return "".join(output)

def render(innerhtml_content):
    """ render html content and return a ascii text. """
    with open("./render.log", "w") as fp :
        fp.write(innerhtml_content)
    parser = MyHTMLParser()
    parser.feed(innerhtml_content)
    return parser.get_output()

def test():
    print("".join(render("<p>hello</p>")))
    with open("/root/xkvim/text.html", "r") as fp :
        lines = fp.readlines()
    print("".join(render("".join(lines))))

if cmd_args.login == "yes": 
    asyncio.get_event_loop().run_until_complete(login())
else: 
    asyncio.get_event_loop().run_until_complete(process_loop(cmd_args.prompt == "yes"))
