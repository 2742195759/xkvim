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
import Debug.Trace (trace)
import qualified Data.Aeson.KeyMap
import Data.Scientific (toBoundedInteger)

data RpcRespond = RpcRespond Int Value String
instance ToJSON RpcRespond where
  toJSON (RpcRespond id res status) = object ["id" .= id, "res" .= res, "status" .= (String $ pack status)] 

hasKeyId :: Value -> Bool
hasKeyId (Object o) = (trace (show o)) isJust $ Data.Aeson.KeyMap.lookup "id" o
hasKeyId _ = False

toNumber :: Value -> Maybe Int
toNumber (Number n) = toBoundedInteger n

getId :: Value -> Int
getId (Object o) = fromJust $ toNumber (fromJust $ Data.Aeson.KeyMap.lookup "id" o)
getId _ = error "bugs!"


rpcHandle :: Socket -> SelectMonad ()
rpcHandle sock = do 
    oneLine <- fromRight "Error, Happens" <$> (lift $ readLine sock)
    if null oneLine 
      then closeHandle sock
      else do
        let json_str = C8.pack oneLine
        let maybe_json = decode (trace ("[Receive Message] " ++ oneLine) json_str) :: Maybe Value
        if isNothing maybe_json || not (hasKeyId $ fromJust maybe_json)
          then lift $ putStrLn $ "Decode Error!: " ++ oneLine
          else do
            let id = getId $ fromJust maybe_json
            let respond = processHandle $ fromJust maybe_json
            lift . putStrLn . show $ respond
            rpcResponse sock id respond

rpcWrite :: Socket -> RpcRespond -> SelectMonad ()
rpcWrite s rsp = (lift $ writeBlock s $ trace ("[Send Message] " ++ msg) msg) >> return ()
    where msg = (show  (encode rsp)) ++ "\n" :: String

rpcResponse :: Socket -> Int -> Either String Value -> SelectMonad ()
rpcResponse sock id (Left status) = do
    rpcWrite sock $ RpcRespond id (String $ pack status) "error"
rpcResponse sock id (Right v) = do 
    rpcWrite sock $ RpcRespond id v "success"

listenHandle :: Socket -> SelectMonad ()
listenHandle sock = do
    (conn, _) <- lift $ accept sock
    lift . print $ "Receive rpc client..., use rpcHandle"
    selectInsert conn rpcHandle

main :: IO ()
main = startSelect (return ()) listenHandle
