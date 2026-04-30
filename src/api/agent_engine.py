import re
from typing import List, Dict, Any

class TechModulAgent:
    """
    Zaawansowany Agent Tekstowy do sterowania parametrami mebli.
    Obsługuje: ustawianie, zwiększanie, zmniejszanie wymiarów (H, W, D).
    """

    def __init__(self, modules_provider):
        self.modules_provider = modules_provider
        self.constraints = {
            "depth": {"min": 100, "max": 1200},
            "width": {"min": 150, "max": 2800},
            "height": {"min": 100, "max": 2500}
        }

    def parse_valuation_sheet(self, text: str) -> List[Dict[str, Any]]:
        """
        Parsuje multiline tekst na listę elementów do wyceny.
        Przykład: "Szafka dolna 600x820x560, dąb 2szt"
        """
        lines = text.split('\n')
        items = []
        
        # Regex szukający wymiarów typu AxBxC lub A x B x C
        dim_pattern = r"(\d+)\s*[xX*]\s*(\d+)\s*[xX*]\s*(\d+)"
        qty_pattern = r"(\d+)\s*(szt|sztuki|sztuk)"
        
        for line in lines:
            if not line.strip(): continue
            
            dim_match = re.search(dim_pattern, line)
            w, h, d = (int(dim_match.group(1)), int(dim_match.group(2)), int(dim_match.group(3))) if dim_match else (600, 720, 560)
            
            qty_match = re.search(qty_pattern, line)
            qty = int(qty_match.group(1)) if qty_match else 1
            
            # Próba wyłuskania materiału
            clean_line = line
            if dim_match: clean_line = clean_line.replace(dim_match.group(0), "")
            if qty_match: clean_line = clean_line.replace(qty_match.group(0), "")
            
            name = clean_line.split(',')[0].strip() or "Element"
            material = ""
            if ',' in clean_line:
                material = clean_line.split(',')[1].strip()
            
            items.append({
                "name": name,
                "width": w,
                "height": h,
                "depth": d,
                "quantity": qty,
                "material_query": material,
                "raw": line.strip()
            })
            
        return items

    def parse_command(self, text: str) -> Dict[str, Any]:
        text = text.lower().strip()
        
        # Regex dla: działanie (zwiększ/zmniejsz) + parametr (głębokość/szerokość/wysokość) + wartość
        pattern = r"(ustaw|zmien|zmień|zwieksz|zwiększ|zmniejsz)?\s*(glebokosc|głębokość|szerokosc|szerokość|wysokosc|wysokość|depth|width|height)\s*(na|o)?\s*(\d+)"
        match = re.search(pattern, text)
        
        if not match:
            return {"action": "unknown"}

        action_type = match.group(1) or "ustaw"
        param = match.group(2)
        value = int(match.group(4))

        # Mapowanie polskiego nazewnictwa na parametry techniczne
        param_map = {
            "glebokosc": "depth", "głębokość": "depth", "depth": "depth",
            "szerokosc": "width", "szerokość": "width", "width": "width",
            "wysokosc": "height", "wysokość": "height", "height": "height"
        }
        
        mapped_param = param_map[param]

        # Określenie operacji
        operation = "set"
        if action_type in ["zwieksz", "zwiększ"]: operation = "add"
        if action_type == "zmniejsz": operation = "sub"

        return {
            "action": "modify_dimension",
            "param": mapped_param,
            "value": value,
            "operation": operation,
            "target": "selected_modules"
        }

    def handle_command(self, text: str):
        cmd = self.parse_command(text)
        
        if cmd["action"] == "modify_dimension":
            modules = self.modules_provider.get_selected_modules()
            preview_changes = []
            
            for m in modules:
                old_val = m.get(cmd["param"], 0)
                new_val = old_val
                
                if cmd["operation"] == "set": new_val = cmd["value"]
                elif cmd["operation"] == "add": new_val = old_val + cmd["value"]
                elif cmd["operation"] == "sub": new_val = old_val - cmd["value"]

                # Walidacja limitów technicznych
                limit = self.constraints.get(cmd["param"])
                if new_val < limit["min"] or new_val > limit["max"]:
                    return {"type": "error", "message": f"Przekroczono limity techniczne dla {cmd['param']} ({limit['min']}-{limit['max']}mm)"}

                preview_changes.append({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "param": cmd["param"],
                    "old": old_val,
                    "new": new_val
                })

            return {
                "type": "preview",
                "action": "modify_dimension",
                "changes": preview_changes
            }

        return {"type": "error", "message": "Nie zrozumiałem polecenia. Spróbuj np. 'zwiększ głębokość o 50'"}

# --- INTEGRACJA Z TWOIM API ---
# W pliku main_api.py dodamy:
# @app.post("/agent/command")
# async def execute_agent_command(data: CommandRequest):
#     return agent.handle_command(data.text)
