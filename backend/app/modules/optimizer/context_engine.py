"""Motor de contexto histórico local, gratuito y determinista.

No requiere API keys ni LLM: usa una base de datos curada de autores para
componer un párrafo de contexto (años, época y un dato biográfico). Si el
autor no está en la base, produce un texto genérico y honesto.
"""

AUTHORS: dict[str, tuple[str, str]] = {
    "Albert Einstein": ("1879-1955", "físico teórico, padre de la relatividad"),
    "J.K. Rowling": ("1965-", "escritora británica, autora de Harry Potter"),
    "Marilyn Monroe": ("1926-1962", "actriz estadounidense, ícono cultural"),
    "Mark Twain": ("1835-1910", "escritor y humorista estadounidense"),
    "Eleanor Roosevelt": (
        "1884-1962",
        "diplomática y activista, primera dama de EE. UU.",
    ),
    "Dr. Seuss": ("1904-1991", "autor infantil estadounidense"),
    "Steve Martin": ("1945-", "comediante, actor y escritor estadounidense"),
    "Elie Wiesel": (
        "1928-2016",
        "escritor, sobreviviente del Holocausto, Nobel de la Paz",
    ),
    "Thomas A. Edison": ("1847-1931", "inventor estadounidense"),
    "Andre Gide": ("1869-1951", "escritor francés, Nobel de Literatura"),
    "Mother Teresa": ("1910-1997", "misionera católica, Nobel de la Paz"),
    "Bob Marley": ("1945-1981", "músico jamaicano, símbolo del reggae"),
    "Jim Rohn": ("1930-2009", "orador motivacional estadounidense"),
    "Charles R. Swindoll": ("1934-", "pastor y autor estadounidense"),
    "Stephen King": ("1947-", "escritor de terror estadounidense"),
    "Oscar Wilde": ("1854-1900", "escritor y dramaturgo irlandés"),
    "Friedrich Nietzsche": ("1844-1900", "filósofo alemán"),
    "William Shakespeare": ("1564-1616", "dramaturgo y poeta inglés"),
    "Martin Luther King Jr.": ("1929-1968", "líder del movimiento de derechos civiles"),
    "Mahatma Gandhi": ("1869-1948", "líder de la independencia de la India"),
    "Winston Churchill": ("1874-1965", "primer ministro británico"),
    "Confucius": ("551-479 a.C.", "filósofo chino"),
    "Aristotle": ("384-322 a.C.", "filósofo griego, discípulo de Platón"),
    "Socrates": ("470-399 a.C.", "filósofo griego clásico"),
    "Helen Keller": ("1880-1968", "escritora y activista estadounidense"),
    "Ralph Waldo Emerson": ("1803-1882", "ensayista y filósofo trascendentalista"),
    "George Bernard Shaw": ("1856-1950", "dramaturgo irlandés, Nobel de Literatura"),
    "Abigail Adams": ("1744-1818", "primera dama de EE. UU. y epistológrafa"),
    "Dalai Lama": ("1935-", "líder espiritual del budismo tibetano"),
    "Napoleon Hill": ("1883-1970", "autor de autoayuda estadounidense"),
    "Albert Schweitzer": ("1875-1965", "médico y filósofo, Nobel de la Paz"),
    "Anne Frank": ("1929-1945", "diarista judía, víctima del Holocausto"),
    "Ayn Rand": ("1905-1982", "filósofa y novelista ruso-estadounidense"),
    "J.M. Barrie": ("1860-1937", "escritor escocés, autor de Peter Pan"),
    "Bruce Lee": ("1940-1973", "artista marcial y actor"),
    "John Lennon": ("1940-1980", "músico británico, miembro de The Beatles"),
    "Frank Zappa": ("1940-1993", "músico y compositor estadounidense"),
    "Hunter S. Thompson": ("1937-2005", "periodista estadounidense, pionero del gonzo"),
    "James Baldwin": ("1924-1987", "escritor y activista estadounidense"),
    "E.E. Cummings": ("1894-1962", "poeta estadounidense"),
    "Rumi": ("1207-1273", "poeta sufí persa"),
    "Aesop": ("620-560 a.C.", "fabulista de la Grecia antigua"),
    "Isaac Newton": ("1643-1727", "físico y matemático inglés"),
    "Blaise Pascal": ("1623-1662", "filósofo, matemático y físico francés"),
    "Khalil Gibran": ("1883-1931", "poeta y ensayista libanés"),
    "Leo Tolstoy": ("1828-1910", "novelista ruso"),
    "John Wooden": ("1910-2010", "entrenador de baloncesto estadounidense"),
    "Zig Ziglar": ("1926-2012", "orador motivacional estadounidense"),
    "Paulo Coelho": ("1947-", "escritor brasileño"),
    "Henri Nouwen": ("1932-1996", "sacerdote y escritor neerlandés"),
    "Epictetus": ("50-135", "filósofo estoico griego"),
    "Roy T. Bennett": ("1963-", "autor de autoayuda"),
    "Haruki Murakami": ("1949-", "escritor japonés"),
    "Anne Lamott": ("1954-", "escritora estadounidense"),
}


class ContextEngine:
    """Compone el contexto histórico de una frase a partir del autor."""

    def explain(self, phrase: str, author: str) -> str:
        entry = AUTHORS.get(author)
        if entry is None:
            return (
                f"Esta cita se atribuye a {author}, aunque la base de datos de "
                "autores no incluye una reseña biográfica de esta persona."
            )
        years, note = entry
        return (
            f"Esta cita se atribuye a {author} ({years}), {note}. "
            "El contexto de la frase refleja el pensamiento y la época de su autor."
        )
