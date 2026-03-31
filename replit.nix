{ pkgs }: {
	deps = [
   pkgs.ruff
		pkgs.tree
		pkgs.nodePackages.pyright
		pkgs.python312
	];
}
