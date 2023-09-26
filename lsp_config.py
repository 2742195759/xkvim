configuration = {
    "servers": {
        "clangd": {
            "filetype": ["c", "cpp", "objc", "objcpp", "cc", "h", "hpp"],
            "rootPatterns": [".git"],
            "initializationOptions": None,
            "languageId": "cpp",
            "executable": "clangd",
            "command": "clangd --background-index=0 --compile-commands-dir={rootUri} -j=10 2>clangd.log",
            "install": None
        }, 
        "jedi": {
            "filetype": ["py"],
            "initializationOptions": None,
            "rootPatterns": [".git"],
            "languageId": "python",
            "executable": "jedi-language-server",
            "command": "jedi-language-server 2>jedi.log",
            "install": None
        },
        "haskell": {
            "filetype": ["hs"],
            "initializationOptions": None,
            "rootPatterns": [".git"],
            "languageId": "haskell",
            "executable": "haskell-language-server-wrapper",
            "command": "haskell-language-server-wrapper -j 5 --debug --cwd {rootUri} --lsp",
            "install": None
        },
        "cmake": {
            "filetype": ["cmake", "txt"],
            "initializationOptions": {
                "buildDirectory": "{rootUri}/build",
            },
            "rootPatterns": [".git"],
            "languageId": "cmake",
            "executable": "cmake-language-server",
            "command": "cmake-language-server",
            "install": "pip install cmake-language-server"
        },
    },
    "client": {
        
    },
}
