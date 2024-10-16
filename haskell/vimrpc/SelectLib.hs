{-# LANGUAGE OverloadedStrings #-}

module SelectLib (
      startSelect 
    , SelectEnv(..)
    , SelectMonad(..)
    , Handle(..)
    , selectInsert
    , selectRemove
    , echoHandle
    , closeHandle,
    ) where

import qualified Control.Exception as E
import qualified Data.ByteString.Char8 as C
import Network.Socket
import System.Posix.IO.Select (select')
import System.Posix.IO.Select.Types
import System.Posix.Types (Fd(..))
import Network.Socket.ByteString (recv, sendAll)
import Control.Monad.Trans.State.Lazy (StateT, modify, runStateT, get)
import Foreign.C.Types (CInt)
import Control.Monad.Trans.Class (lift)
import Data.Map as M
import System.Posix.Env (getEnv)

type Handle = (Socket -> SelectMonad ())
type SockMap = M.Map Foreign.C.Types.CInt (Socket, Handle)
data SelectEnv = SelectEnv {
    sockMap :: SockMap
}
type SelectMonad = StateT SelectEnv IO


selectInsert :: Socket -> Handle -> SelectMonad ()
selectInsert sock handle = do
    fd <- lift $ fdSocket sock
    modify $ \(SelectEnv map) -> 
        SelectEnv $ M.insert fd (sock, handle) map


selectRemove :: Socket -> SelectMonad ()
selectRemove sock = do
    fd <- lift $ fdSocket sock
    modify $ \(SelectEnv map) -> 
        SelectEnv $ M.delete fd map


echoHandle :: Handle
echoHandle sock = do
    msg <- lift $ recv sock 1024
    if msg == C.pack "" then do 
        closeHandle sock
    else do
      lift $ print $ "[FromSocket]: " ++ show sock
      lift $ print msg

closeHandle :: Handle
closeHandle sock = do
  lift . print $ "closing socket" ++ show sock
  selectRemove sock

sendDataToSocket :: Socket -> Socket -> SelectMonad ()
sendDataToSocket from to = do
    msg <- lift $ recv from 1024
    lift . print $ msg
    if msg == C.pack "" then do 
      lift $ print "closed by other peer."
      lift $ sendAll to msg
      selectRemove from
      selectRemove to
    else do
      lift $ sendAll to msg

initProcess :: SelectMonad () -> Handle -> SelectMonad ()
initProcess initHandle listenHandle = do 
    mhost <- lift $ getEnv "HOST"
    mport <- lift $ getEnv "PORT"
    let host = maybe "127.0.0.1" id mhost
    let port = maybe "3000" id mport
    lift $ putStrLn $ "listening " ++ host ++ ":" ++ port
    addr <- lift $ resolve host port
    server <- lift $ doListen addr
    selectInsert server listenHandle 
    initHandle
  where 
    resolve host port = do
        let hints = defaultHints { addrSocketType = Stream }
        addr:_ <- getAddrInfo (Just hints) (Just host) (Just port)
        return addr

    doConnect addr = do
        sock <- socket (addrFamily addr) (addrSocketType addr) (addrProtocol addr)
        connect sock $ addrAddress addr
        return sock

    doListen addr = do 
        sock <- socket (addrFamily addr) (addrSocketType addr) (addrProtocol addr)
        bind sock $ addrAddress addr
        listen sock 10
        return sock

startSelect :: SelectMonad () -> Handle -> IO ()
startSelect initHandle listenHandle = withSocketsDo $ do
    {-E.bracket (open addr) close loop-}
    print ("start select server ...")
    loop $ initProcess initHandle listenHandle  
  where
    loop :: SelectMonad() -> IO ()
    loop init = do 
        (_, env) <- runStateT init (SelectEnv M.empty)
        loop' env

    loop' :: SelectEnv -> IO ()
    loop' env = do
        let fds = Fd <$> (M.keys $ sockMap env)
        res <- select' fds [] [] (Time $ CTimeval 1 0)  
        (_, new_env) <- case res of 
            Nothing -> runStateT (return ()) env
            Just (rs, ws, es) -> runStateT (deal (sockMap env) rs) env 
        loop' new_env

    deal :: SockMap -> [Fd] -> SelectMonad ()
    deal dict [] = return ()
    deal dict ((Fd x):xs) = do 
        let maybe_handler = M.lookup x dict
        case maybe_handler  of 
          Nothing -> E.throw $ E.AssertionFailed "key errors."
          Just (sock, handle) -> do
            handle sock
        deal dict xs
