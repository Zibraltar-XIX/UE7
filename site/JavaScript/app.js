const express = require('express');
const mysql = require('mysql2');
const cookieParser = require('cookie-parser');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.urlencoded({ extended: true }));
app.use(cookieParser());

const db = mysql.createConnection({
  host: '127.0.0.1',
  user: 'alternance',
  password: 'mdptahlesfous',
  database: 'main'
});

db.connect(err => {
  if (err) throw err;
  console.log('Connecté à MySQL');
});

app.listen(3000, () => console.log('Serveur sur port 3000'));

app.post('/login', (req, res) => {
  const { email, password } = req.body; 

  db.query('SELECT id FROM users WHERE email = ? AND password = ?', [email, password], (err, results) => {
    if (err) {
      return res.status(500).send('Erreur DB');
    }
    
    if (results.length > 0) {
      const userId = results[0].id;

      res.cookie('sessionCookie', userId.toString(), {
        maxAge: 3600000,     
        httpOnly: false,     
        secure: false,       
        sameSite: 'none'    
      });
      
      res.redirect('/profile');  
    } else {

      res.redirect('/login?error=1');
    }
  });
});