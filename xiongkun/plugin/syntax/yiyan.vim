syntax region  Input  start="^yiyan>"hs=s+7 end="$"
syntax region  Code   start="```" end="```"

hi link Code   SignColumn
hi link Input  ErrorMsg

