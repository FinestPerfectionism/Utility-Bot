{ pkgs }: {
	deps = [
		pkgs.tree
		pkgs.nodePackages.pyright
		pkgs.python312
	];
}
