let s:trigger = {}

fu! s:trigger.Trigger(arglist)
  if self.m_on == 0
    let self.m_on = 1
    cal self.f_open(a:arglist)
  else 
    let self.m_on = 0
    cal self.f_close(a:arglist)
  endif
endf

fu! trigger#New(open, close)
  let res = deepcopy(s:trigger)
  let res.f_open = a:open
  let res.f_close = a:close
  let res.m_on = 0
  return res
endf

