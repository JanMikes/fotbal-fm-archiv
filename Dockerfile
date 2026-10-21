FROM php:8.5-apache

# The official image ships no php.ini (PHP defaults: display_errors=1, expose_php=1).
# Use the bundled production ini: errors are logged (to docker logs), never displayed.
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && echo "expose_php = Off" > "$PHP_INI_DIR/conf.d/zz-production.ini"

RUN a2enmod rewrite \
    && sed -i 's/AllowOverride None/AllowOverride All/g' /etc/apache2/apache2.conf

# Copy layers from least to most frequently changed
COPY --chown=www-data:www-data web/assets/ /var/www/html/assets/
COPY --chown=www-data:www-data web/pages/ /var/www/html/pages/
COPY --chown=www-data:www-data web/index.php web/.htaccess /var/www/html/
COPY --chown=www-data:www-data web/page_map.json web/esports_map.json web/esports_checked.json web/esports_map_v3.json /var/www/html/

EXPOSE 80
