module RegisterHandle (autoGenDataType, createProcesser) where

{-# LANGUAGE TemplateHaskell #-}

import RegisterUtil
import Language.Haskell.TH
import Language.Haskell.TH.Lib
import Data.Aeson
import Data.Aeson.Types
import Control.Monad
import GHC.Utils.Misc
import Data.Maybe
import Data.Either
import Data.Vector (toList)
import qualified Data.Aeson.Key as DAK
import qualified Data.Aeson.KeyMap as KeyMap
import Debug.Trace (trace)

parseJsonBody :: (Quote m) => Name -> [Name] -> m Exp
parseJsonBody dataName typeNames = do 
    (patterns, vars) <- gen_Patterns_And_Vars $ length typeNames
    let argNum = litE $ IntegerL $ toInteger $ length typeNames
    let parsed_vars = map (\v->appE (varE 'parseJSON) v) vars
        toTuple x   = listP x
    let typename = conE dataName
    [| (\v -> do 
            let isArgNumMatch x = trace ("Arg Number is:" ++ (show . length $ x)) $ length x == $(argNum)
            let isArray (Array a) = True
                isArray _ = False
            if isArray v
              then do 
                   let (Array a) = v
                   let x = toList a
                   if isArgNumMatch x 
                     then let $(toTuple patterns) = x 
                          in  $(applyTupleVarsMonad (appE (varE 'pure) typename) parsed_vars)
                     else fail "Argument Number is not match."
              else
                fail "Param is not a array."
         )
      |]
   
aesonInstance :: (Quote m) => Name -> [Name] -> m Dec
aesonInstance dataName typeNames = instanceD (return []) (appT (conT ''FromJSON) (conT dataName)) [parseJson]
    where parseJson = funD (mkName "parseJSON") [ clause [] (normalB $ parseJsonBody dataName typeNames) [] ]

normalBang :: Bang
normalBang = Bang NoSourceUnpackedness NoSourceStrictness

autoGenDataType :: (Quote m) => String -> [Name] -> m [Dec]
autoGenDataType method args = sequence [return dataTypeDecl, aesonInstance dataName args, argNumFuncDecl]
    where dataName = getParamName method :: Name
          boundTypes = map (\t->((normalBang, ConT t))) args
          dataTypeDecl = DataD [] dataName [] Nothing [NormalC dataName boundTypes] [DerivClause Nothing [ConT ''Show]]
          argNumFuncDecl = funD (getArgNumFuncName method) [clause [] (normalB $ litE $ IntegerL $ toInteger $ length args) []]  

gen_Patterns_And_Vars :: (Quote m) => Int -> m ([m Pat], [m Exp])
gen_Patterns_And_Vars n = do 
    retNames <- forM [1..n] (\x->newName "r")
    return (fmap varP retNames, fmap varE retNames)

applyTupleVars :: (Quote m) => m Exp -> [m Exp] -> m Exp
applyTupleVars f (x:xs) = applyTupleVars (appE f x) xs
applyTupleVars f [] = f

applyTupleVarsMonad :: (Quote m) => m Exp -> [m Exp] -> m Exp
applyTupleVarsMonad f (x:xs) = applyTupleVarsMonad (applicative_apply f x) xs
    where applicative_apply a b = [| $a <*> $b |]
applyTupleVarsMonad f [] = f

eachMatchExpr ::  (Quote m) => String -> Name -> Int -> m Match
eachMatchExpr method handleName numArgs = do 
    varName <- newName "x"
    let methodPattern = litP $ StringL method
    let paramType = conT $ getParamName method
    let applyHandle = [e| $(varE handleName) |]
    (retPatterns, varPatterns) <- gen_Patterns_And_Vars numArgs
    match methodPattern (normalB 
        [| let eitherRequest = parseEither parseJSON . getParam $ v :: Either String $(paramType)
               $(conP (getParamName method) retPatterns) = fromRight (error "Error") eitherRequest
               isArgNumberMatch ($(conP (getParamName method) retPatterns)) = True
               isArgNumberMatch _ = False
           in  if isLeft eitherRequest
                 then Left $ fromLeft ("Error") eitherRequest
                 else if (isArgNumberMatch $ fromRight (error "Error") eitherRequest)
                        then Right $ toJSON $ $(applyTupleVars applyHandle varPatterns)
                        else Left "Not match arguments."
          |]) []

genFunctionRenameDec :: (Quote m) => Name -> Name -> m [Dec]
genFunctionRenameDec ori new = return $ [FunD new [Clause [] (NormalB $ VarE ori) []]] 

createProcesser :: (Quote m) => String -> [(String, Name, Int)] -> m [Dec]
createProcesser processName handles = do 
    let matches = map (\(xs)->uncurry3 eachMatchExpr xs) handles 
    let notFoundMethodCase = match [p| methodName |] (normalB [| Left $ "Method `" ++ methodName ++ "` Not Found." |]) []
    let caseBody = caseE [e| fromJust $ maybeMethod v |] (matches ++ [notFoundMethodCase])
    decs <- [d| 
        process :: Value -> Either String Value
        process v = if hasMethod v && hasParam v
                      then $(caseBody)
                      else Left "Decode failed while get method."
            where maybeMethod (Object o) = parseMaybe (\o->o .: (DAK.fromString "method")) o :: Maybe String
                  maybeMethod _ = Nothing
                  maybeParam (Object o) = o KeyMap.!? (DAK.fromString "param") :: Maybe Value
                  maybeParam _ = Nothing
                  hasMethod v = isJust $ maybeMethod v
                  hasParam v = isJust $ maybeParam v
                  getParam v = fromJust $ maybeParam v
        |]
    let (SigD unique_process_name _) = head decs
    (++) <$> (return decs) <*> genFunctionRenameDec unique_process_name (mkName processName)

