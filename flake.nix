{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, utils, ... }:
    utils.lib.eachDefaultSystem (
      system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        packages.default = pkgs.python3Packages.buildPythonApplication {
          name = "axyn";
          src = ./.;

          postPatch = ''
            substituteInPlace axyn/__main__.py \
              --replace facebook/opt-350m ${pkgs.callPackage ./model.nix {}}
          '';

          propagatedBuildInputs = with pkgs.python3Packages; [ torch transformers ];
        };
      }
    );
}
