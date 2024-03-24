{-# LANGUAGE OverloadedStrings #-}
module Main where 
import Rpc (processHandle)
import SelectLib (startSelect
                , SelectEnv(..)
                , echoHandle
                , selectInsert
                , SelectMonad(..)
                , closeHandle
                )
import Network.Socket
import Network.Stream
import Network.StreamSocket
import Data.Either
import Data.Maybe
import Control.Monad.Trans.Class (lift)
import qualified Data.ByteString as BS
import qualified Data.ByteString.Lazy.Char8 as C8
import Data.Aeson
import Data.Text (pack)

data RpcRespond = RpcRespond Value String
instance ToJSON RpcRespond where
  toJSON (RpcRespond res status) = object ["res" .= res, "status" .= (String $ pack status)] 

rpcHandle :: Socket -> SelectMonad ()
rpcHandle sock = do 
    oneLine <- fromRight "Error, Happens" <$> (lift $ readLine sock)
    if null oneLine 
      then closeHandle sock
      else do
        let json_str = C8.pack oneLine
        let maybe_json = decode json_str :: Maybe Value
        if isNothing maybe_json 
          then lift $ putStrLn $ "Decode Error!: " ++ oneLine
          else do
            let respond = processHandle $ fromJust maybe_json
            {-lift . putStrLn . show $ respond -}
            rpcResponse sock respond

rpcWrite :: Socket -> RpcRespond -> SelectMonad ()
rpcWrite s rsp = (lift $ writeBlock s $ show $ encode rsp) >> return ()

rpcResponse :: Socket -> Either String Value -> SelectMonad ()
rpcResponse sock (Left status) = do
    rpcWrite sock $ RpcRespond (String $ pack status) "error"
rpcResponse sock (Right v) = do 
    rpcWrite sock $ RpcRespond v "success"

listenHandle :: Socket -> SelectMonad ()
listenHandle sock = do
    (conn, _) <- lift $ accept sock
    lift . print $ "Receive rpc client..., use rpcHandle"
    selectInsert conn rpcHandle

main :: IO ()
main = startSelect (return ()) listenHandle
