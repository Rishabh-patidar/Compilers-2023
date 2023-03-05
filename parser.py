from fractions import Fraction
from dataclasses import dataclass
from typing import Optional, NewType
from sim import *
from lexer import *
from error import Error

# Global value denoting if the Parse Error occured
isParseError = False

class ParseException(Exception):
    '''
    Class for parse exception to be caught by parse_program
    '''
    pass

@dataclass
class Parser:
    
    lexer: Lexer # Lexer to produce the tokens
    
    def ParseError(self, message_: str, lineNumber: int, type_: str="ParseError"):
        '''
        Way to report Parse Error
        '''
        # Reporting the error
        Error(type_ , message_, lineNumber).report()

        # Synchronizing the lexer
        self.lexer.synchronize()

        # Raising the parseException to be caught using parse program
        raise ParseException

    def from_lexer(lexer):
        return Parser(lexer)
    
    def parse_if(self):
        self.lexer.match(Keyword(0, "if"))
        self.lexer.match(Operator(0, "("))
        c = self.parse_expr()
        self.lexer.match(Operator(0, ")"))
        self.lexer.match(Operator(0, "{"))
        ifseq=[]
        while(self.lexer.peek_token().val != "}") :
            t = self.parse_declare()
            ifseq.append(t)
        self.lexer.match(Operator(0,"}"))
        if(self.lexer.peek_token().val != "else"):
            return If(c, Seq(ifseq), None)
        self.lexer.match(Keyword(0, "else"))
        self.lexer.match(Operator(0, "{"))
        elseq=[]
        while(self.lexer.peek_token().val != "}") :
            t = self.parse_declare()
            elseq.append(t)
        self.lexer.match(Operator(0, "}"))
        return If(c,Seq(ifseq), Seq(elseq))

    def parse_for(self):
        self.lexer.match(Keyword(0, "for"))
        self.lexer.match(Operator(0, "("))
        bf = self.lexer.peek_token()
        initial = nil()
        if(self.lexer.peek_token().val in dtypes):
            initial = self.parse_vardec()
        elif (bf.val == ";") :
            self.lexer.advance()
        else:
            initial = self.parse_expr_stmt()

        condition = self.parse_expr()
        self.lexer.match(Operator(0, ";"))
        bf = self.lexer.peek_token()
        
        order = nil()
        if (bf.val != ")") :
            order = self.parse_expr()

        self.lexer.match(Operator(0, ")"))
        self.lexer.match(Operator(0, "{"))


        forseq = []
        while(self.lexer.peek_token().val != "}") :
            t = self.parse_declare()
            forseq.append(t)
        self.lexer.match(Operator(0, "}"))

        if (order != nil()):
            forseq.append(order)
            
        return For(initial,condition,Seq(forseq))
        
    
    def parse_while(self):
        self.lexer.match(Keyword(0, "while"))
        self.lexer.match(Operator(0, "("))
        c = self.parse_expr()
        self.lexer.match(Operator(0, ")"))
        self.lexer.match(Operator(0, "{"))
        wseq=[]
        while(self.lexer.peek_token().val != "}") :
            t = self.parse_declare()
            wseq.append(t)
        self.lexer.match(Operator(0, "}"))
        return While(c, Seq(wseq))
    
    def parse_print(self):
        self.lexer.match(Keyword(0, "zout"))
        self.lexer.match(Operator(0, "("))
        pseq=[]
        pseq.append(self.parse_expr())
        while(self.lexer.peek_token().val != ")"):
            self.lexer.match(Operator(0, ","))
            t=self.parse_expr()
            pseq.append(t)
        self.lexer.match(Operator(0, ")"))
        self.lexer.match(Operator(0, ";"))
        return PRINT(pseq)
    
    def parse_expr_stmt(self):
        t = self.parse_expr()
        self.lexer.match(Operator(0, ';'))
        return t
    
    def parse_atom(self):
        match self.lexer.peek_token():
            case Identifier(lineNumber, name):
                self.lexer.advance()
                return Variable(name)
            case Integer(lineNumber, value):
                self.lexer.advance()
                return Int(value)
            case Boolean(lineNumber, value):
                self.lexer.advance()
                return Bool(value)
            case String(lineNumber, value):
                self.lexer.advance()
                return Str(value)
            case Flt(lineNumber, value):
                self.lexer.advance()
                return Float(value)
            case Operator(lineNumber, '('):
                self.lexer.advance()
                l = self.parse_expr()
                self.lexer.match(Operator(0, ')'))
                return l
            case other:
                self.ParseError("Expected an Expression!", other.lineNumber)
    
    def parse_unary(self):
        op = self.lexer.peek_token()
        if(op.val in ["~","-"]) :
            self.lexer.advance()
            right = self.parse_unary()
            return UnOp(right,op.val)
        return self.parse_atom()
    
    def parse_mult(self):
        left = self.parse_unary()
        while True:
            match self.lexer.peek_token():
                case Operator(lineNumber, op) if op in "*/":
                    self.lexer.advance()
                    m = self.parse_unary()
                    left = BinOp(op, left, m)
                case _:
                    break
        return left
    
    def parse_add(self):
        left = self.parse_mult()
        while True:
            match self.lexer.peek_token():
                case Operator(lineNumber, op) if op in ["+","-"]:
                    self.lexer.advance()
                    m = self.parse_mult()
                    left = BinOp(op, left, m)
                case _:
                    break
        return left
    
    def parse_comparision(self):
        left = self.parse_add()
        while(isinstance(self.lexer.peek_token(), Operator) and self.lexer.peek_token().val in ["<",">",">=","<="]):
            op = self.lexer.peek_token().val
            self.lexer.advance()
            right = self.parse_add()
            left =  BinOp(op, left, right)
        return left
    
    def parse_equality(self):
        left = self.parse_comparision()
        while(self.lexer.peek_token().val in ["!=","=="]) :
            t = self.lexer.peek_token()
            self.lexer.advance()
            right = self.parse_comparision()
            left = BinOp(t.val,left,right)
        return left
    
    def parse_logic_and(self) :
        left = self.parse_equality()
        while(self.lexer.peek_token().val == "&&"):
            self.lexer.advance()
            right = self.parse_equality()
            left = BinOp("&&",left,right)
        return left
    
    def parse_logic_or(self) :
        left = self.parse_logic_and()
        while(self.lexer.peek_token().val == "||" ) :
            self.lexer.advance()
            right = self.parse_logic_and()
            left = BinOp('||',left,right)
        return left
    
    def parse_assign(self):
        l = self.parse_logic_or()
        a = self.lexer.peek_token()
        if (a.val == "=") :
            self.lexer.advance()
            t = self.parse_assign()
            return BinOp("=",l,t)
        return l
    
    def parse_expr(self):
        return self.parse_assign()
    
    def parse_statement(self):
        
        match self.lexer.peek_token():
            case Keyword(lineNumber, "if"):
                return self.parse_if()
            case Keyword(lineNumber, "while"):
                return self.parse_while()
            case Keyword(lineNumber, "zout"):
                return self.parse_print()
            case Keyword(lineNumber, "for"):
                return self.parse_for()
            case _:
                return self.parse_expr_stmt()
            
    def parse_vardec(self):
        
        found=None
        l=self.lexer.peek_token()
        if(l.val == "const"):
            self.lexer.match(l)
            found=True
        else:
            found=False
        match self.lexer.peek_token():
            case Keyword(lineNumber, "int"):
                self.lexer.match(Keyword(0, "int"))
                b = self.lexer.peek_token()
                if(b.val in keywords or b.val in dtypes or b.val in ["true","false"]):
                    self.ParseError("Expected a '=' or ';'", lineNumber)
                self.lexer.match(b)
                if(self.lexer.peek_token().val != "="):
                    self.lexer.match(Operator(0, ";"))
                    return Declare(Variable(b.val), nil(), Int, found)
                self.lexer.match(Operator(0, "="))
                ans=self.parse_expr_stmt()
                return Declare(Variable(b.val),ans, Int, found)
            case Keyword(lineNumber, "float"):
                self.lexer.match(Keyword(0, "float"))
                b=self.lexer.peek_token()
                if(b.val in keywords or b.val in dtypes or b.val in ["true","false"]):
                    self.ParseError("Expected a '=' or ';'", lineNumber)
                self.lexer.match(b)
                if(self.lexer.peek_token().val != "="):
                    self.lexer.match(Operator(";"))
                    return Declare(Variable(b.val),nil(), Float, found)
                self.lexer.match(Operator(0, "="))
                ans=self.parse_expr_stmt()
                return Declare(Variable(b.val),ans, Float, found)
            case Keyword(lineNumber, "string"):
                self.lexer.match(Keyword(0, "string"))
                b=self.lexer.peek_token()
                if(b.val in keywords or b.val in dtypes or b.val in ["true","false"]):
                    self.ParseError("Expected a '=' or ';'", lineNumber)
                self.lexer.match(b)
                if(self.lexer.peek_token().val != "="):
                    self.lexer.match(Operator(";"))
                    return Declare(Variable(b.val),nil(), Str, found)
                self.lexer.match(Operator(0,"="))
                ans=self.parse_expr_stmt()
                return Declare(Variable(b.val),ans, Str , found)
            case Keyword(lineNumber, "boolean"):
                self.lexer.match(Keyword(0, "boolean"))
                b=self.lexer.peek_token()
                if(b.val in keywords or b.val in dtypes or b.val in ["true","false"]):
                    self.ParseError("Expected a '=' or ';'", lineNumber)
                self.lexer.match(b)
                if(self.lexer.peek_token().val !="="):
                    self.lexer.match(Operator(0, ";"))
                    return Declare(Variable(b.val),nil(), Bool, found)
                self.lexer.match(Operator(0, "="))
                ans=self.parse_expr_stmt()
                return Declare(Variable(b.val),ans, Bool , found)
            
    def parse_declare(self):
        if(self.lexer.peek_token().val not in dtypes):
            return self.parse_statement()
        else:
            return self.parse_vardec()
    
    def parse_program(self):
        seqs=[]
        while(self.lexer.peek_token() != EOF()) :
            # Using try except for catching the ParseException as well as TokenException
            try:
                seqs.append(self.parse_declare())
            except (ParseException, TokenException):
                global isParseError
                isParseError = True
        return Seq(seqs)

def parse(string):
    '''
    Return a Parsed AST as well as the isParseError flag corresponding to parsing
    '''
    # Reinitializing the isParseError to False
    global isParseError 
    isParseError = False

    # Returning the obtained AST as well as the flag isParseError
    return Parser.parse_program (
        Parser.from_lexer(Lexer.from_stream(Stream.from_string(string)))
    ), isParseError

def test_parse():
    print(parse("for (;i<10;i=i+1){zout(i);}")) 

if __name__ == "__main__" :
    test_parse()
