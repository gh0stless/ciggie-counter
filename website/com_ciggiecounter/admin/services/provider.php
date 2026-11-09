<?php

/**
 * @package     CrazyMidi.Administrator
 * @subpackage  com_ciggiecounter
 *
 * @copyright   (C) 2026 crazy-midi.de
 * @license     GPL-3.0-or-later
 */

defined('_JEXEC') or die;

use CrazyMidi\Component\Ciggiecounter\Administrator\Extension\CiggiecounterComponent;
use Joomla\CMS\Extension\ComponentInterface;
use Joomla\CMS\Extension\Service\Provider\ComponentDispatcherFactory;
use Joomla\CMS\Extension\Service\Provider\MVCFactory;
use Joomla\CMS\Dispatcher\ComponentDispatcherFactoryInterface;
use Joomla\CMS\MVC\Factory\MVCFactoryInterface;
use Joomla\DI\Container;
use Joomla\DI\ServiceProviderInterface;

/**
 * Mirrors com_globalrandom's own services/provider.php (a real, working
 * component already installed on this same server) as closely as possible -
 * no RouterFactory/RouterServiceInterface registration, since that
 * component doesn't need one either and it's one less thing to get wrong.
 */
return new class implements ServiceProviderInterface {
    public function register(Container $container): void
    {
        $namespace = '\\CrazyMidi\\Component\\Ciggiecounter';

        $container->registerServiceProvider(new ComponentDispatcherFactory($namespace));
        $container->registerServiceProvider(new MVCFactory($namespace));

        $container->set(
            ComponentInterface::class,
            function (Container $container) {
                $component = new CiggiecounterComponent(
                    $container->get(ComponentDispatcherFactoryInterface::class)
                );
                $component->setMVCFactory($container->get(MVCFactoryInterface::class));

                return $component;
            }
        );
    }
};
