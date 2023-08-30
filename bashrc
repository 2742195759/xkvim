# Locales

export LC_ALL=zh_CN.UTF-8
export LANG=zh_CN.UTF-8
export LANGUAGE=zh_CN.UTF-8

# Aliases
#

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

alias ls='ls -hFG'
alias l='ls -lF'
alias ll='ls -alF'
alias lt='ls -ltrF'
alias ll='ls -alF'
alias lls='ls -alSrF'
alias llt='ls -altrF'

# Colorize directory listing

alias ls="ls -ph --color=auto"

# Colorize grep

if echo hello|grep --color=auto l >/dev/null 2>&1; then
   TMP_GREP_OPTIONS="--color=auto" GREP_COLOR="1;31"
fi
alias grep='grep ${TMP_GREP_OPTIONS}'


# Shell

export CLICOLOR="1"

YELLOW="\[\033[1;33m\]"
NO_COLOUR="\[\033[0m\]"
GREEN="\[\033[1;32m\]"
WHITE="\[\033[1;37m\]"

source ~/.scripts/git-prompt.sh

export PS1="\[\033[1;33m\]λ $WHITE\h $GREEN\w$YELLOW\$(__git_ps1 \" \[\033[35m\]{\[\033[36m\]%s\[\033[35m\]}\")$NO_COLOUR "

# Git

source ~/.scripts/git-completion.sh

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/opt/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<
TERM=xterm-256color
export PYTHONIOENCODING=utf-8
export PATH=$PATH:/usr/local/bin

git config --global user.email xiongkun03@baidu.com
git config --global user.name xiongkun
git config --global push.default current
git config --global credential.helper store
export PATH=$PATH:$HOME/xkvim/bash_scripts:$HOME/xkvim/cmd_script

