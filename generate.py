import sys
from crossword import *

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            values = self.domains[var].copy()
            for value in values:
                if len(value) != var.length:
                    self.domains[var].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        if self.crossword.overlaps[x, y]:
            xvalues = self.domains[x].copy()
            for xval in xvalues:
                valid = False
                yvalues = self.domains[y].copy()
                for yval in yvalues:
                    if xval == yval:
                        continue
                    if xval[self.crossword.overlaps[x, y][0]] == yval[self.crossword.overlaps[x, y][1]]:
                        valid = True
                if not valid:
                    self.domains[x].remove(xval)
                    revised = True
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = arcs
        if not queue:
            queue = []
            for x in self.domains:
                for y in self.domains:
                    if x == y:
                        continue
                    queue.append((x, y))

        while queue:
            (x, y) = queue.pop(0)
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                for z in self.crossword.neighbors(x) - {y}:
                    queue.append((z, x))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if len(assignment) != len(self.crossword.variables):
            return False
        for var in assignment:
            if not assignment[var]:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for var1 in assignment:
            # Check values are the right length
            if len(assignment[var1]) != var1.length:
                return False
            # Check all values are different
            for var2 in assignment:
                if var1 == var2:
                    continue
                if assignment[var1] == assignment[var2]:
                    return False
            # Check conflicts between neighbours
            for neighbour in self.crossword.neighbors(var1):
                overlap = self.crossword.overlaps[var1, neighbour]
                if neighbour not in assignment:
                    continue
                if assignment[var1][overlap[0]] != assignment[neighbour][overlap[1]]:
                    return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        def constraint(var, value):
            """
            For a given variable and value, returns the number of
            choices that are ruled out for neighbouring variables
            """
            constrained = 0
            for neighbour in self.crossword.neighbors(var):
                if value in self.domains[neighbour]:
                    constrained += 1
            return constrained

        domain_values = []
        for value in self.domains[var]:
            domain_values.append(value)

        # Sort domain values by least constraining value heuristic
        return sorted(domain_values, key=lambda value: constraint(var, value))


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_variables = []
        for var in self.domains:
            if var not in assignment:
                unassigned_variables.append(var)

        unassigned_variables = sorted(unassigned_variables, key=lambda variable: self.crossword.neighbors(variable), reverse=True)
        unassigned_variables = sorted(unassigned_variables, key=lambda variable: len(self.domains[variable]))

        #print(unassigned_variables)
        return unassigned_variables[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            assignment[var] = value
            domains_copy = self.domains.copy()
            inferences = []
            if self.consistent(assignment):
                # Inference by maintaining arc consistency
                arcs = []
                for neighbour in self.crossword.neighbors(var):
                    arcs.append((neighbour, var))
                self.ac3(arcs)
                # Add to assignment any known values
                for domain_var in self.domains:
                    if len(self.domains[domain_var]) == 1:
                        assignment[domain_var] = self.domains[domain_var].pop()
                        inferences.append(domain_var)

                result = self.backtrack(assignment)
                if result:
                    return result
            # If no result, inferences must be removed
            for inference in inferences:
                del assignment[inference]
            self.domains = domains_copy.copy()
            del assignment[var]
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
