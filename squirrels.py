from abc import ABC, abstractmethod

class Squirrel(ABC):
    """Абстрактная белка - задаёт правила для всех белок"""

    def __init__(self, name, age):
        self.name = name
        self.age = age

    @abstractmethod
    def make_sound(self):
        """Каждая белка должна издавать свой звук"""
        pass

    @abstractmethod
    def move(self):
        """Каждая белка должна двигаться по-своему"""
        pass

    def eat(self):
        """Общий метод для всех белок (не абстрактный)"""
        print(f"{self.name} грызёт орешек!")

class CommonSquirrel(Squirrel):
    """Обычная белка - дочерний класс от Squirrel"""
    def __init__(self, name, age, color):
        Squirrel.__init__(self, name, age)
        self.color = color

    def make_sound(self):
        print(f"{self.name} ({self.color}): Цок-цок-цок!")

    def move(self):
        print(f"{self.name} прыгает с ветки на ветку")

class FlyingSquirrel(Squirrel):
    """Белка-летяга - дочерний класс от Squirrel"""

    def __init__(self, name, age, wing_span):
        Squirrel.__init__(self, name, age)
        self.wing_span = wing_span

    def make_sound(self):
        print(f"{self.name}: Пиииии! (тихое цоканье в полёте)")

    def move(self):
        print(f"{self.name} планирует в воздухе (размах {self.wing_span} см)")

    def glide(self):
        """Новый метод только для летяги"""
        print(f"{self.name} расправила перепонки и парит!")

class Chipmunk(Squirrel):
    """Бурундук - дочерний класс от Squirrel"""

    def __init__(self, name, age, stripes):
        Squirrel.__init__(self, name, age)
        self.stripes = stripes

    def make_sound(self):
        print(f"{self.name}: ЦОК-ЦОК! (очень громко!!!)")

    def move(self):
        print(f"{self.name} быстро бегает по земле")

    def store_food(self):
        """Новый метод только для бурундука"""
        print(f"{self.name} набивает щёки орешками (полосок: {self.stripes})")

if __name__ == "__main__":
    print("НАШ ЗВЕРИНЕЦ")
    print()

    squirrel = CommonSquirrel("Белка", 2, "белка")
    flyer = FlyingSquirrel("Летяга", 3, 45)
    chip = Chipmunk("Бурундук", 1, 5)

    animals = [squirrel, flyer, chip]

    for animal in animals:
        print("Кто:", animal.name, "возраст:", animal.age, "лет")

        animal.make_sound()
        animal.move()
        animal.eat()

        if isinstance(animal, FlyingSquirrel):
            animal.glide()

        if isinstance(animal, Chipmunk):
            animal.store_food()
        print()
    print("Программа завершена!")
