{%r = request.post_params()%}
{%obj = [(1, 2), (3, 4)]%}
<html>
  <head>
    <title>{%=r.get('a', 'this is title')%}</title>
    <script type="text/javascript" src="http://img3.douban.com/js/packed_jquery.min0.js"></script>
    <script type="text/javascript">
    {%
def info(request, post):
    print post
    return [(5, 6), (7, 8)]
%}
      $.post('?func=info', {'a': 'b', 'c': 'd'}, function(data){
          var json = eval(data);
          for(var i = 0; i < json.length; i++){
              var tr = $("<tr>");
              for(var j = 0; j < json[i].length; j++){
                  var td = $("<td>").html(json[i][j]);
                  tr.append(td);
              }
              $("#main").append(tr);
          }
      });
    </script>
  </head>{%
def index(b):
    print b
    return 0
%}
  <body>
    <table id="main">
      <tr>
        <td>col1</td>
        <td>col2</td>
      </tr>{%for i in obj:%}
      <tr>
        <td>{%=i[0]%}</td>
        <td>{%=i[1]%}</td>
      </tr>{%end%}
      <tr>
        <td>{%=index('idx1')%}</td>
        <td>{%=index('idx2')%}</td>
      </tr>
    </table>
  </body>
</html>
