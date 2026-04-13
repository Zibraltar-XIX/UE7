SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+01:00";

CREATE DATABASE IF NOT EXISTS main;
USE main;

CREATE TABLE IF NOT EXISTS `Annonce` (
`id` int(11) NOT NULL,
  `id_Utilisateur` int(11) DEFAULT NULL,
  `Description` text,
  `Titre` tinytext,
  `Contrat` enum('Alternance','Stage') DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 AUTO_INCREMENT=1 ;


CREATE TABLE IF NOT EXISTS `Utilisateurs` (
`id` int(11) NOT NULL,
  `Prenom` tinytext,
  `Nom` tinytext,
  `Telephone` varchar(20) DEFAULT NULL,
  `Email` tinytext,
  `Role` varchar(20) DEFAULT NULL,
  `MotDePasse` varchar(255) DEFAULT NULL,
  `Adresse` text,
  `Web` text,
  `Linkedin` varchar(20) DEFAULT NULL,
  `Github` varchar(20) DEFAULT NULL,
  `Portfolio` varchar(20) DEFAULT NULL,
  `Loisirs` text,
  `Competences` text,
  `Emplois` text,
  `Description` text,
  `CV` text,
  `PdP` text,
  `LM` text
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 AUTO_INCREMENT=1 ;

ALTER TABLE `Annonce`
 ADD PRIMARY KEY (`id`);

ALTER TABLE `Utilisateurs`
 ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `Telephone` (`Telephone`);

ALTER TABLE `Annonce`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `Utilisateurs`
MODIFY `id` smallint(6) NOT NULL AUTO_INCREMENT;