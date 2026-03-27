FROM php:8.2-apache

RUN a2enmod rewrite \
    && sed -i 's/AllowOverride None/AllowOverride All/g' /etc/apache2/apache2.conf

# Copy layers from least to most frequently changed
COPY --chown=www-data:www-data web/assets/ /var/www/html/assets/
COPY --chown=www-data:www-data web/pages/ /var/www/html/pages/
COPY --chown=www-data:www-data web/index.php web/.htaccess /var/www/html/
COPY --chown=www-data:www-data web/page_map.json web/esports_map.json web/esports_checked.json web/esports_map_v3.json /var/www/html/

EXPOSE 80
