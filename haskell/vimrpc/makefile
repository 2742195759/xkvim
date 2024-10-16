target: Main.hs RegisterHandle.hs
	ghc --make -XTemplateHaskell Main.hs -o main -ddump-splices # -ddump-to-file

requirement: makefile
	cabal install --lib HTTP
	cabal install --lib select
	cabal install --lib aeson
	cabal install --lib network
	cabal install --lib vector
	cabal install --lib split
	cabal install --lib scientific

clean: 
	rm -f main
	rm -f *.dyn_o
	rm -f *.o
	rm -f *.hi
	rm -f *.dyn_hi
	rm -f *.dump-splices
	
