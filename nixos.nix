self:
{ pkgs, ... }:

let
  axyn = self.packages.${pkgs.system}.default;

in {
  systemd.services.axyn = {
    description = "Axyn Discord chatbot";
    wantedBy = [ "default.target" ];
    serviceConfig.Restart = "on-failure";
    script = ''
      export DISCORD_TOKEN="$(cat /var/lib/axyn-discord-token)"
      exec ${axyn}/bin/axyn
    '';
  };
}
