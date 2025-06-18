


output = '''
text
{
    "title": "O Livro dos Hábitos que Mudam o Mundo",
    "author": "Leticia Lavares",
    "language": "Português",
    "review": "Um livro sobre virtudes para jovens leitores, explorando como os hábitos podem moldar o mundo. A capa sugere uma jornada de descoberta e o desenvolvimento de um senso de direção, possivelmente através da adoção de valores e práticas positivas. Uma leitura inspiradora para quem busca impactar o mundo ao seu redor."
}
```
'''

print(output)
extracted_data = {}
lines = output.split('\n')

for line in lines:
            if "title" in line:
                extracted_data["title"] = line.split('"title":')[1].strip()
            elif "author" in line:
                extracted_data["author"] = line.split('"author":')[1].strip()
            elif "language" in line:
                extracted_data["language"] = line.split('"language":')[1].strip()
            elif "review" in line:
                extracted_data["review"] = line.split('"review":')[1].strip()

print(extracted_data)