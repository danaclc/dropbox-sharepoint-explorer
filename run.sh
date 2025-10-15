#/bin/sh
directories=(
  "ACRD"
  "Archives"
  "Commun"
  "Compta"
  "Direction ACC M"
  "Ferroviaire"
  "Informatique"
  "Logistique"
  "PAO"
  "Qualité"
  "SRH"
  "SST"
  "STG"
)

for dir in "${directories[@]}"; do
    #uv run explore -p "$dir" -s "$dir"
    uv run explore -c "$dir"
done
