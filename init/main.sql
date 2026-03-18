SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE DATABASE IF NOT EXISTS main;
USE main;

CREATE TABLE IF NOT EXISTS `anonce` (
`id` int(11) NOT NULL,
  `id_user` int(11) DEFAULT NULL,
  `description` text,
  `title` tinytext,
  `contrac` enum('Alternance','Stage') DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;


CREATE TABLE IF NOT EXISTS `user` (
`id` smallint(6) NOT NULL,
  `First-Name` tinytext,
  `Last-Name` tinytext,
  `phone` varchar(20) DEFAULT NULL,
  `email` tinytext,
  `Role` varchar(20) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `adresse` text,
  `web` text,
  `hobbies` text,
  `skills` text,
  `jobs` text,
  `description` text,
  `cv` blob,
  `pdp` blob,
  `lm` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

ALTER TABLE `anonce`
 ADD PRIMARY KEY (`id`);

ALTER TABLE `user`
 ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `phone` (`phone`);

ALTER TABLE `anonce`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `user`
MODIFY `id` smallint(6) NOT NULL AUTO_INCREMENT;