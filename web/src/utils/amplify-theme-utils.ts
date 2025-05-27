import { Theme } from '@aws-amplify/ui-react';

const createCustomTheme = (tokens: any): Theme => {
  return {
    name: 'Starfish Data Theme',
    tokens: {
      components: {
        authenticator: {
          router: {
            boxShadow: `0 0 16px ${tokens.colors.overlay['10']}`,
            borderWidth: '0',
          },
          form: {
            padding: `${tokens.space.medium} ${tokens.space.xl} ${tokens.space.medium}`,
          },
        },
        button: {
          primary: {
            backgroundColor: tokens.colors.pink['40'],
            _hover: {
              backgroundColor: tokens.colors.pink['80'],
            },
            _active: {
                backgroundColor: tokens.colors.pink['100'],
            },
            _focus: {
                backgroundColor: tokens.colors.pink['80'],
            },
          },
          link: {
            color: tokens.colors.pink['40'],
            _hover: {
              color: tokens.colors.pink['80'],
            },
          },
          _hover: {
            color: tokens.colors.pink['10'],
            backgroundColor: tokens.colors.pink['80'],
          },
        },
        fieldcontrol: {
          _focus: {
            boxShadow: `0 0 0 2px ${tokens.colors.pink['60']}`,
          },
        },
        tabs: {
          item: {
            color: tokens.colors.neutral['80'],
            _active: {
              borderColor: tokens.colors.neutral['100'],
              color: tokens.colors.pink['100'],
            },
          },
        },
      },
    },
  };
};

export default createCustomTheme;
