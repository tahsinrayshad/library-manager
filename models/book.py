from db_connection import Connection

class Book:
    def __init__(self, title, author, year):
        self.title = title
        self.author = author
        self.year = year

    def __str__(self):
        return f"'{self.title}' by {self.author} ({self.year})"
    
    def __repr__(self):
        return f"Book(title='{self.title}', author='{self.author}', year='{self.year}')"

    def to_dict(self):
        return {
            "title": self.title,
            "author": self.author,
            "year": self.year
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data["title"], data["author"], data["year"])
    
    def save_to_db(self):
        query = "INSERT INTO books (title, author, year) VALUES (?, ?, ?)"
        try:
            with Connection.cursor(commit=True) as cur:
                cur.execute(query, (self.title, self.author, self.year))
            return True
        except Exception as e:
            print(f"Error saving to DB: {e}")
            return False