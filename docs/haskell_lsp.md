## Haskell Language Server Installation

### Linux M1-Arm installation documentation

在 Mac 的 docker linux 环境下安装 haskell 的 安装步骤。

良好的haskell开发环境需要如下两个：

1. Haskell 的开发工具栈
2. Haskell 支持的一个 Editor

这里 Editor 我们使用 vim ，工具tool chain 我们使用 GHCup 管理器提供的一个安装包来安装。

##### 安装 GHCup 和必要的工具

包含编译器 ghc、交互式 ghci 和 haskell language server .

1. 登录：[ghcup安装官方网站](https://www.haskell.org/ghcup/#)

2. 执行下列代码行：

```bash
apt install build-essential curl libffi-dev libffi7 libgmp-dev libgmp10 libncurses-dev
apt install -y curl libnuma-dev
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh
```

可以看到如下的输出，则表示正在进行安装中：
```text
[ Info  ] downloading: https://raw.githubusercontent.com/haskell/ghcup-m
as file /root/.ghcup/cache/ghcup-0.0.7.yaml
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  
                                 Dload  Upload   Total   Spent    Left  
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--
[ Info  ] downloading: https://downloads.haskell.org/~ghc/9.2.7/ghc-9.2.
file /root/.ghcup/cache/ghc-9.2.7-aarch64-deb10-linux.tar.xz
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  
                                 Dload  Upload   Total   Spent    Left  
 46  264M   46  123M    0     0  2278k      0  0:01:58  0:00:55  0:01:03
 47  264M   47  126M    0     0  2278k      0  0:01:58  0:00:56  0:01:02
 51  264M   51  135M    0     0  2277k      0  0:01:58  0:01:00  0:00:58 2262kkk
```

3. 安装完毕之后，需要将路径暴露出来，给 bashrc 添加如下的代码。
```bash
export PATH=$PATH:/root/.ghcup/bin
export PATH=$PATH:/root/.ghcup/hls/1.10.0.0/bin/
```

4. 配置vim coc中的Language Server: 在 Vim 中输入 :CocConfig . 具体的配置网站可以如下网站: [Haskell Language Server](https://haskell-language-server.readthedocs.io/en/latest/configuration.html)
```vim
{
  "languageserver": {
    "haskell": {
      "command": "haskell-language-server-wrapper",
      "args": ["--lsp"],
      "rootPatterns": [ "*.cabal", "stack.yaml", "cabal.project", "package.yaml", "hie.yaml" ],
      "filetypes": ["haskell", "lhaskell"],
      "settings": {
        "haskell": {
          "checkParents": "CheckOnSave",
          "checkProject": true,
          "maxCompletions": 40,
          "formattingProvider": "ormolu",
          "plugin": {
            "stan": { "globalOn": true }
          }
        }
      }
    }
  }
}
```

