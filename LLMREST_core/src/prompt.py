SYSTEM_PROMPT = """
You are an expert in the field of RESTful API testing. 
You will be provided with information about the API under test, and you will be asked to provide answers to 
questions related to the API.
"""

SYS_IDL = """
You are a helpful assistant, helping handle the issues related to RESTful APIs.
In RESTful API, there are constraint relationships between several parameters, 
we use IDL(Inter-parameter Dependency Language) to describe constraints.
The IDL syntax is as follows:

Model:
    Dependency*;
Dependency:
    RelationalDependency | ArithmeticDependency |
    ConditionalDependency | PredefinedDependency;
RelationalDependency:
    Param RelationalOperator Param;
ArithmeticDependency:
    Operation RelationalOperator DOUBLE;
Operation:
    Param OperationContinuation |
    '(' Operation ')' OperationContinuation?;
OperationContinuation:
    ArithmeticOperator (Param | Operation);
ConditionalDependency:
    'IF' Predicate 'THEN' Predicate;
Predicate:
    Clause ClauseContinuation?;
Clause:
    (Term | RelationalDependency | ArithmeticDependency
    | PredefinedDependency) | 'NOT'? '(' Predicate ')';
Term:
    'NOT'? (Param | ParamValueRelation);
Param:
    ID | '[' ID ']';
ParamValueRelation:
    Param '==' STRING('|'STRING)* |
    Param 'LIKE' PATTERN_STRING | Param '==' BOOLEAN |
    Param RelationalOperator DOUBLE;
ClauseContinuation:
    ('AND' | 'OR') Predicate;
PredefinedDependency:
    'NOT'? ('Or' | 'OnlyOne' | 'AllOrNone' |
    'ZeroOrOne') '(' Clause (',' Clause)+ ')';
RelationalOperator:
    '<' | '>' | '<=' | '>=' | '==' | '!=';
ArithmeticOperator:
    '+' | '-' | '*' | '/';


Here are the explanation of some basic relations of IDL:

Case1: Or(param_1, param_2)
One of the two parameters is required. One must be present in the API call, but not both.

Case2: AllOrNone(param_1, param_2,...,param_n)
All of the parameters or none of them must be present in the API call.

Case3: OnlyOne(param_1, param_2,...,param_n)
Exactly only one of the parameters must be present in the API call.
If there are only two parameters, it is equivalent to Or(param_1, param_2), use OR instead of OnlyOne.

Case4: ZeroOrOne(param_1, param_2,...,param_n)
At most one of the parameters can be present in the API call.

Case5 : param_1>= param_2
There is an arithmetic relationship between parameters, the relational operators can be >,>=,<,<=,==,!=

Case6: IF param_1 THEN param_2
There is a conditional relationship between parameters, If param_1 is present in the API call, param_2 must be present.

Case7: IF Case_m THEN Case_n
There exists a complex relationship between parameters, the rule can be combined.


I will give you the name and description of the parameters that might have constraints in Info, 
and i will give the name of all parameters in a list, extract constraints from the descriptions, if any.

Note:
1. Not all parameters are in Info are constrained, it’s just that we suspect there may be constraints.
   Check carefully to see if there are any constraints.
2. Pay attention to the reference relationship. 
   In some descriptions, the names that are the same as some parameters do not point to specific parameters.
3. Ignore the Deprecated parameters. If (Deprecated) appears in the description, it means the parameter is deprecated.
"""

OPERATION_PROMPT = """
You wil be provided with the name of the operations of the API under test.

Dependency Rules:
In RESTful API, an operation usually consists of a http verb and an url.
HTTP verbs include post, put get, delete, patch, etc. 
For the same URL, post must be executed first and delete must be executed last. get, put, patch is better to be
executed after post and before delete for the same URL.
Different URLs may have hierarchical structures, such as /users and /users/name.
Usually longer URLs often depend on shorter URLs, so the operation of longer URLs often needs to be between 
post and delete of shorter URLs.
There may also be dependencies between some URLs that do not have a hierarchical relationship. 
For example, some operations need to use the data results obtained by another operation.

Operations:{}
To Test:{}

Explanation:
1. Operations: All the operations of the API under test.
2. To Test: The operations that to be tested, it may be not tested or failed.

Your task:
- Generate a sequence of operations that test the operations in the "To Test" list. Format your answer as a JSON object.
  The format is sequence: [operation1, operation2, operation3, ...].

Note:
1. Pay attention to the dependencies between operations. Make sure the sequence is correct.
"""

IDL_PROMPT = """
Parameter List: {}
Info: {}    

Your task:
- Give the IDL constraint of the constraint parameters.
  Format your response as a JSON object.
  The format is constraints: [expression1, expression2, ...].
  If there is no constraint, return an empty list.
"""

VALUE_PROMPT = """
Now I will explain the information to be provided.
1. Request is the method and base url of a RESTful API request.
2. Parameter info is a list contains python dicts, records the corresponding operation's parameter information of the 
   request. Each dict corresponds to a parameter, recording the information.
   Note the parameter name is the last part of the parameter's global name in the info, like  'body.name' is 'name'. If 
   it ends with '_item'. like 'body.name._item', it means it's an array parameter, the name is 'name'.
3. Sentence Constraint records the constraint relationships of the parameters. 
   If empty, there is no constraint.
4. Responses is a list of previous responses of the operation. It may contains the format of parameters. If empty, 
    there is no response.
   
Request: {}
Parameter info: {}
Constraint: {}
Responses: {}

Your task:
- Try to give 2 possible values for each parameter in Parameter info that are different from the generated value.
  If the description of the parameter contains example values, extract the example values first. The example value of 
  one parameter may appear in other parameters' descriptions.
  Format your response as a JSON object.
  The format is parameter1's global name:[value1,value2,...],parameter2's global name:[value1,value2,...],....
  
Pay attention:
1. Name of the parameter, if it appears in the response string, please identify it and according to the 
   response to give the value. 
2. The specific format of the value, if it appears in the description or the response, please give the value
    in the prescribed format.
"""

DEPENDENCY_PROMPT = """
In RESTful API, an operation usually consists of a http verb and an url.

HTTP verbs include post, put get, delete, patch, etc. 
For the same URL, post must be executed first and delete must be executed last.

Different URLs may have hierarchical structures, such as /users and /users/name. 
Usually longer URLs often depend on shorter URLs, so the operation of longer URLs often 
needs to be between post and delete of shorter URLs.

In Restful API, there may be dependencies between different operations, the parameter values of some operations
may depend on the results of other operations. According to the HTTP verb and URL, or the description of the operation, 
you can infer the dependencies between the operations.

I will give you operation name and description of the operation to be tested and the operation that has been successfully
tested, and you need to infer the dependencies between the operations.

Operation: {}
Previous operation: {}

Your task: 

According to the infos, infer which operations in the Previous operation the Operation depends on, and give at most 2 
possible operations. Format your response as a JSON object. 
The format is dependent_operations: [operation1, operation2].
Note that if the Operation does not depend on any operation, return an empty list.
"""

BIND_PROMPT = """
I will give the name of an operation and the parameter info of it, and the response of the operations that it depends 
on.

Operation: {}
Parameter info: {}
Dependent operation response parameter: {}
"""

BIND_TASK = """
Your task:
- Try to find which response parameter of the dependent operation is related to the parameter of the operation. Give the 
possible binding relationship. Format your response as a JSON object. 
The format is {parameter1:{op1: param in response, op2: param in response},param2:{}...}.
If there is no binding relationship, return an empty object.

Note:
1. Not all parameters in the Parameter info have dependencies, but carefully read the descriptions of the 
parameters, do not miss the dependencies.
"""

initial_sequence = """
You are an expert in RESTful API testing and help me solve problems in testing.
In RESTful API, an operation usually consists of a http verb and an url.
HTTP verbs include post, put get, delete, patch, etc. 

1. For the same URL, post must be executed first and delete must be executed last.

Different URLs may have hierarchical structures, such as /users and /users/name. 

2. Usually longer URLs often depend on shorter URLs, so the operation of longer URLs often needs to be between 
post and delete of shorter URLs.

I will give you a list of REST operations, including the operation name and description of it

Operation List: {}

Your task:
- Based on the the given operations, give one sequence of operations that can execute correctly.
  Pay attention to the dependencies between operations.
  Note that just use the operations given in Operation List.
  Format your response as a JSON object.
  The format is sequence: [operation1, operation2, ...].
"""

BINDING = """
You are a helpful assistant, helping handle the issues related to RESTful APIs. 

In RESTful API, an operation usually consists of a http verb and an url.
HTTP verbs include post, put get, delete, patch, etc. 
For the same URL, post must be executed first and delete must be executed last.
Different URLs may have hierarchical structures, such as /users and /users/name. 
Usually longer URLs often depend on shorter URLs, so the operation of longer URLs often 
needs to be between post and delete of shorter URLs.

In Restful API, there may be dependencies between different operations. 
Especially the path parameter of an operation, its parameter value may come from the server feedback after the previous 
operation was successful.

I will give you the parameter information of the path parameter of the RESTful API operation that you need to handle, 
along with the name of the previous successful operation(arranged in order of execution). 

operation: {}
Parameter info: {}
Previous operation: {}

Your task: 
According to the name of previous operation and the information of the path parameter, 
infer the results of which operations the values of these parameters may depend on.
Answer at most likely operation.
Format you answer as a JSON object.
The format is param1:operation, param2:operation, ....
Use only the operations in the previous operation list.
If the parameter value does not depend on any previous operation, the value is None.
"""

FIND_PARAM = """
I will give you the response param name or the response info of the previous operation.

{}

"""

FIND_PARAM_TASK = """
Your task:
1. Try to give the parameter name which value should be the same as which parameter in the response.
   Format your answer as JSON object. 
   The format is {param1:{operation1:param_in_response, operation2:param_in_response}..., param2:{},...}
   Only use the operations I provide the response.
"""

ORACLE = """
You are an expert in RESTful API testing and help me solve problems in testing.

We usually use the status code of the response to determine whether the operation is successful or not in RESTful API 
testing. However, there are some exceptions. For example, the status code of the response is 200, but the response is 
not what we expected. In this case, we need to check the response content to determine whether the operation is
correctly executed.

I will give the parameter information of the operation to be tested, the response information of the operation.

Operation: {}
Parameter info: {}
Response info: {}

Your task:
- Try to give the correspondence between the parameter and the response parameter. Pay attention to the parameter
  description and type of the parameter and response parameter.
  Format your response as a JSON object.
  The format is param1:response_param1, param2:response_param2,...
  Just return the parameters that have a relationship with the response.
"""
