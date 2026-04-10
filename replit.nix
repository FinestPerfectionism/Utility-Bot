{ pkgs }: {
	deps = [
   pkgs.python312Packages.isort
   pkgs.ruff
		pkgs.tree
		pkgs.nodePackages.pyright
		pkgs.python312
	];
}
