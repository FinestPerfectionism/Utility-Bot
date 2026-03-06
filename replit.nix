{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.replitPackages.pyproject-nix
    pkgs.nodePackages.typescript-language-server
  ];
}
