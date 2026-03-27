```python
class TestAI:
    """
    Prosta klasa testuj─ůca sztuczn─ů inteligencj─Ö.
    """

    def __init__(self, name="TestAI"):
        """
        Inicjalizator klasy TestAI.

        Args:
            name (str, optional): Nazwa instancji TestAI. Domy┼Ťlnie "TestAI".
        """
        self.name = name
        self.result = 0

    def process_data(self, data):
        """
        Procesuje dane i zwraca wynik.

        Args:
            data (int): Dane do przetworzenia.

        Returns:
            int: Wynik przetwarzania danych.
        """
        self.result = data * 2
        return self.result

    def get_name(self):
        """
        Zwraca nazw─Ö instancji TestAI.

        Returns:
            str: Nazwa instancji.
        """
        return self.name

    def reset_result(self):
        """
        Resetuje wynik do zera.
        """
        self.result = 0

if __name__ == '__main__':
    # Przyk┼éadowe u┼╝ycie klasy TestAI
    ai_instance = TestAI("MojAI")
    ai_instance.process_data(5)
    print(f"Wynik przetwarzania danych przez {ai_instance.get_name()}: {ai_instance.result}") # Output: Wynik przetwarzania danych przez MojAI: 10
    ai_instance.reset_result()
    print(f"Wynik po zresetowaniu: {ai_instance.result}") # Output: Wynik po zresetowaniu: 0
```
