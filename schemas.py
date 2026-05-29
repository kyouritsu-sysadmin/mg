

SCHEMA_DESCRIPTION = """
{
  "project_title": "string",
  "design_firm": "string",
  "date": "int",
  "cubicle_info": [
    {
      "cubicle_name": "string",
      "power_specification": "string",
      "cubicle_type": "string"
    }
  ],
  "cubicle_count": integer,
  "project_location": "string",
  "transformer_count": integer,
  "transformers": [
    {
      "power_rating_kva": number or null,
      "primary_voltage_kv": number or null,
      "secondary_voltage_v": number or null,
      "specifications": "string or null"
    }
  ],
  "confidence": "high | medium | low"
}
"""