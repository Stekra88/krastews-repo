def get_string_similarity(string1, string2):

    if len(string1) == 0 or len(string2) == 0:
        return 0

    i = 0
    for char in string1:
        if char == string2[i]:
            i += 1
        else:
            break
    percentage = (i*100) / len(string1)
    return percentage



def main():

    string1 = 'asdfghjklp'
    string2 = 'asdf'

    print(get_string_similarity(string1, string2))


